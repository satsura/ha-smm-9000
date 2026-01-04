# Home Assistant Integration for Grand Meyer SMM-9000

Home Assistant integration for controlling Grand Meyer SMM-9000 snow melting system.

## ✅ Status

**Integration is fully ready for use!**

All API methods have been found, tested, and implemented:
- ✅ Device connection via WebSocket
- ✅ Authentication
- ✅ Zone information retrieval
- ✅ Zone control (on/off)
- ✅ Sensor values (temperature, precipitation)

## 🚀 Installation

### Via HACS (Recommended)

If the integration is added to a Git repository:

1. Install **HACS** (if not already installed): https://hacs.xyz
2. In HACS → **Integrations** → **Custom repositories**
3. Add your repository URL:
   - Repository: `https://github.com/your-username/ha-smm-9000`
   - Category: **Integration**
4. Find **Grand Meyer SMM-9000** and install
5. Restart Home Assistant
6. Add the integration via **Settings → Devices & Services**

### Manual Installation

#### Quick Installation:

1. **Copy the folder** `custom_components/smm_9000` to the `custom_components` directory of your Home Assistant:
   
   **For Home Assistant OS/Container:**
   ```bash
   # Via SSH
   scp -r custom_components/smm_9000 root@your-ha-ip:/config/custom_components/
   
   # Or via Samba (Windows Network)
   # Copy to \\homeassistant\config\custom_components\
   ```
   
   **For Home Assistant Core:**
   ```bash
   cp -r custom_components/smm_9000 ~/.homeassistant/custom_components/
   ```

2. **Restart Home Assistant** (required!)

3. Go to **Settings → Devices & Services → Add Integration**

4. Find **"Grand Meyer SMM-9000"** in the list and click

5. Enter parameters:
   - **Device IP address** (e.g., `192.168.1.166`)
   - **Password** (e.g., `12345678`)

6. Click **Submit**

Done! Zones will appear as switches in Home Assistant, and sensors will appear as sensor entities.

## Configuration

To configure the integration, you will need:
- **Device IP address** (e.g., 192.168.1.166)
- **Password** for authentication (default: 12345678)

## Features

- **Zone control** via switches
- **Automatic discovery** of all device zones
- **Real-time state updates** via WebSocket
- **Sensor values** for temperature and precipitation
- **Home Assistant automation support**

## API Methods

### Working Methods

1. **LOGIN_USER** - Authentication (returns sess_id)
2. **DEFAULTS_GET** - Get basic information
3. **HOME_DATA_GET** - Get zone and sensor data
4. **HOME_DATA_SET** - Control zones
5. **ZONES_DATA_SET** - Alternative zone control method

## Development

The integration uses:
- `websockets` for WebSocket connections
- Data Update Coordinator for data update management
- Switch entities for zone control
- Sensor entities for sensor values

## Project Structure

```
ha-smm-9000/
├── custom_components/
│   └── smm_9000/          # Home Assistant integration code
├── README.md              # This file
└── hacs.json              # HACS metadata
```

## Support

If you encounter issues:
1. Check Home Assistant logs
2. Ensure the device is accessible on the network
3. Verify the IP address and password are correct

## License

MIT
