# Hubitat Home Automation

Home automation system managed via Hubitat Elevation hub and Raspberry Pi.

## Components

### Raspberry Pi (192.168.1.190)
- SSH profile: `pi`
- Runs automated blind control via cron job

### Hubitat Elevation (192.168.1.210)
- Maker API: App ID 344
- Controls Somfy MyLink shades

### Weather Hub (192.168.1.180)
- Provides weather data (temperature, wind, solar irradiance)

## Blinds Automation

Script: `blinds.py`

Controls solar blinds based on:
- Sun position (azimuth/altitude)
- Outdoor temperature (>40°F)
- Wind speed (<15 mph)
- Solar irradiance (>150 W/m2)

Blinds are lowered when sun is on a given side of the house:
- South-facing blinds: sun azimuth 270°-360° or 0°-90°
- West-facing blinds: sun azimuth 0°-180°
- North-facing blinds: sun azimuth 90°-272°
- East-facing blinds: sun azimuth 180°-360°

### Cron Job
Runs every 5 minutes via `/etc/cron.d/blinds`

### Location
- Latitude: 40.25241886212485
- Longitude: -111.63855869671522

## Setup

1. Copy `.env.example` to `.env` and fill in values
2. Ensure SSH access to Pi is configured
3. Deploy blinds.py to Pi at `/home/pi/home-automation/`
4. Install Python dependencies in venv

## Dependencies

- pyhubitat
- pyowm
- astropy
- requests
