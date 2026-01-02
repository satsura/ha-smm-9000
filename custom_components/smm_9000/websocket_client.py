"""WebSocket client for SMM-9000 device."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed

from .const import DEFAULT_TIMEOUT, METHOD_LOGIN, METHOD_DEFAULTS_GET, METHOD_HOME_DATA_GET

_LOGGER = logging.getLogger(__name__)


class SMM9000WebSocketClient:
    """WebSocket client for SMM-9000 device."""

    def __init__(self, host: str, password: str, message_callback: Callable[[dict], None] | None = None) -> None:
        """Initialize the WebSocket client."""
        self.host = host
        self.password = password
        self.message_callback = message_callback
        self.ws: WebSocketClientProtocol | None = None
        self.connected = False
        self.sess_id: int | None = None
        self._receive_task: asyncio.Task | None = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._request_id = 0
        self._lock = asyncio.Lock()
        self.sess_id: int | None = None

    def _get_request_id(self) -> str:
        """Get next request ID."""
        self._request_id += 1
        return str(self._request_id)

    async def _receive_messages(self) -> None:
        """Receive messages from WebSocket."""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    _LOGGER.debug("Received message: %s", data)

                    # Обработка ответов на запросы
                    if "method" in data:
                        method = data.get("method")
                        if method in self._pending_requests:
                            future = self._pending_requests.pop(method)
                            if not future.done():
                                future.set_result(data)

                    # Вызов callback для всех сообщений
                    if self.message_callback:
                        # Callback должен быть синхронным, запускаем в executor если нужно
                        try:
                            self.message_callback(data)
                        except Exception as e:
                            _LOGGER.error("Error in message callback: %s", e)

                except json.JSONDecodeError:
                    _LOGGER.error("Failed to parse message: %s", message)
                except Exception as e:
                    _LOGGER.error("Error handling message: %s", e)

        except ConnectionClosed:
            _LOGGER.info("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            _LOGGER.error("Error receiving messages: %s", e)
            self.connected = False

    async def _login(self) -> None:
        """Perform login."""
        try:
            response = await self.send_request(METHOD_LOGIN, {"password": self.password}, require_auth=False)
            if response and response.get("success"):
                self.sess_id = response.get("data", {}).get("sess_id")
                _LOGGER.info("Login successful, sess_id: %s", self.sess_id)
            else:
                _LOGGER.error("Login failed: %s", response)
        except Exception as e:
            _LOGGER.error("Login error: %s", e)

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if self.connected:
            return

        url = f"ws://{self.host}/"
        additional_headers = {
            "Origin": f"http://{self.host}",
        }

        try:
            self.ws = await websockets.connect(url, additional_headers=additional_headers)
            self.connected = True
            _LOGGER.info("WebSocket connected")

            # Запускаем задачу для приема сообщений
            self._receive_task = asyncio.create_task(self._receive_messages())

            # Выполняем авторизацию
            await self._login()

        except Exception as e:
            _LOGGER.error("Failed to connect: %s", e)
            self.connected = False
            raise

    async def send_request(self, method: str, data: dict[str, Any], timeout: int = DEFAULT_TIMEOUT, require_auth: bool = True) -> dict[str, Any] | None:
        """Send request and wait for response."""
        if not self.connected or not self.ws:
            _LOGGER.error("WebSocket not connected")
            return None

        request: dict[str, Any] = {"method": method, "data": data}
        
        # Добавляем sess_id если требуется авторизация и она выполнена
        if require_auth and self.sess_id is not None:
            request["sess_id"] = self.sess_id

        # Создаем future для ожидания ответа
        future = asyncio.Future()
        # Используем method как ключ для простоты
        self._pending_requests[method] = future

        try:
            async with self._lock:
                message = json.dumps(request)
                _LOGGER.debug("Sending message: %s", message)
                await self.ws.send(message)

            # Ждем ответа с таймаутом
            response = await asyncio.wait_for(future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            _LOGGER.error("Request timeout for method: %s", method)
            self._pending_requests.pop(method, None)
            return None
        except Exception as e:
            _LOGGER.error("Error sending request: %s", e)
            self._pending_requests.pop(method, None)
            return None

    async def send_message(self, method: str, data: dict[str, Any], require_auth: bool = True) -> None:
        """Send message without waiting for response."""
        if not self.connected or not self.ws:
            _LOGGER.error("WebSocket not connected")
            return

        request: dict[str, Any] = {"method": method, "data": data}
        
        # Добавляем sess_id если требуется авторизация и она выполнена
        if require_auth and self.sess_id is not None:
            request["sess_id"] = self.sess_id
        
        message = json.dumps(request)
        _LOGGER.debug("Sending message: %s", message)
        try:
            async with self._lock:
                await self.ws.send(message)
        except ConnectionClosed:
            _LOGGER.error("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            _LOGGER.error("Error sending message: %s", e)
            self.connected = False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self.connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                _LOGGER.debug("Error closing WebSocket: %s", e)
            self.ws = None

        _LOGGER.info("WebSocket disconnected")
