#!/home/pi/home-automation/venv/bin/python
import os
import time as mytime
from pprint import pprint
from pyowm import OWM
from pyhubitat import MakerAPI
import astropy.units as u
from astropy.time import Time
from datetime import datetime
from astropy.coordinates import EarthLocation, AltAz
from astropy.coordinates import get_sun
import requests

BRIAR_LAT = float(os.environ['BRIAR_LAT'])
BRIAR_LON = float(os.environ['BRIAR_LON'])
HUB_TOKEN = os.environ['HUBITAT_TOKEN']
HUB_IP = os.environ['HUBITAT_IP']
HUB_APP_ID = os.environ['HUBITAT_APP_ID']
HUB_URL = f'https://{HUB_IP}/apps/api/{HUB_APP_ID}'
MIN_SOLAR_IRRADIANCE = 150
MIN_TEMPERATURE = 40
MAX_GUST_SPEED = 15
WEATHER_HUB_IP = os.environ['WEATHER_HUB_IP']
WEATHER_HUB_URL = f'http://{WEATHER_HUB_IP}/get_livedata_info'


def filter_open_windows(blinds_to_lower):
    filtered_blinds_to_lower = []
    blind_to_sensor_mapping = {
        485: [402], # office east
        486: [403], # office south
        487: [404], # laundry
        488: [405,406], # sam south
        491: [407], # annie south
        492: [408], # annie west
        494: [410], # primary west
        493: [409] # primary north
    }
    ph = MakerAPI(HUB_TOKEN, HUB_URL)
#    print(ph)
    for blind in blinds_to_lower:
        found_open_window = False
#        if blind in blind_to_sensor_mapping:
#            for sensor in blind_to_sensor_mapping[blind]:
#                device_details = ph.get_device_info(sensor)
#                mytime.sleep(2)  # throttle API calls
#                current_state = next((elm['currentValue'] for elm in device_details['attributes'] if elm['name'] == 'contact'), None)
#                if current_state == 'open':
#                    found_open_window = True
        if not found_open_window:
            filtered_blinds_to_lower.append(blind)
    return filtered_blinds_to_lower



def set_blinds(blinds_to_lower):
    ph = MakerAPI(HUB_TOKEN, HUB_URL)
    devices = ph.list_devices()
    blinds = [d for d in devices if d['name'] == "Somfy MyLink Shade"]
#    pprint(blinds)
    directions = blinds_to_lower.split()
    blind_ids_to_lower = []
    for elm in [b for b in blinds for direction in directions if direction in b['label']]:
        blind_ids_to_lower.append(int(elm['id']))
    blind_ids = [int(elm['id']) for elm in blinds]
    blind_ids_to_raise = list(set(blind_ids) - set(blind_ids_to_lower))
    blind_ids_to_lower = filter_open_windows(blind_ids_to_lower)
#    pprint(blind_ids_to_raise)
#    pprint(blind_ids_to_lower)
    for id in blind_ids_to_lower:
#        print(f"lowering blind {id}\n")
        ph.send_command(id, 'close')
        mytime.sleep(2)  # throttle API calls
    for id in blind_ids_to_raise:
#        print(f"opening blind {id}\n")
        ph.send_command(id, 'open')
        mytime.sleep(2)  # throttle API calls


def get_local_weather():
    """
    Fetch local weather data from the specified endpoint and extract:
    - Outdoor temperature (common_list, id 0x02)
    - Wind speed (common_list, id 0x0B)
    - Gust speed (common_list, id 0x0C)
    - Solar irradiance (common_list, id 0x15)
    - Rain rate (piezoRain, id 0x0E)
    Returns a dict with these values (as strings, with units if present).
    """
    url = WEATHER_HUB_URL
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error fetching local weather: {e}")
        return None

    result = {}
    # Extract from common_list
    common = {item['id']: item for item in data.get('common_list', [])}
    result['outdoor_temp'] = common.get('0x02', {}).get('val')
    result['wind_speed'] = common.get('0x0B', {}).get('val')
    result['gust_speed'] = common.get('0x0C', {}).get('val')
    result['solar_irradiance'] = common.get('0x15', {}).get('val')
    # Extract from piezoRain
    piezo = {item['id']: item for item in data.get('piezoRain', [])}
    result['rain_rate'] = piezo.get('0x0E', {}).get('val')
    return result


# get sun angles etc at our location
briar_house = EarthLocation.from_geodetic(BRIAR_LON, BRIAR_LAT, 0)
utcoffset = -6 * u.hour  # Mountain daylight time
time = Time(datetime.utcnow(), scale='utc', location=briar_house)
aaframe = AltAz(obstime=time, location=briar_house)
sun = get_sun(time)
sunaa = sun.transform_to(aaframe)

blinds_to_lower = ''

# if sun is up
# Change if statement to temporarily disable blinds:
# if sunaa.alt > 8.0 * u.deg and False:
if sunaa.alt > 8.0 * u.deg:
    # determine sun's angle with house
    house_angle = 145 * u.deg
    front_angle = sunaa.az - house_angle
    if front_angle < 0: front_angle = front_angle + 360 * u.deg

    # get local weather
    weather = get_local_weather()
    if weather is not None:
        try:
            # Parse temperature (F)
            outdoor_temp = float(weather['outdoor_temp']) if weather['outdoor_temp'] else None
            # Parse gust speed (mph, may include 'mph' in string)
            gust_speed = weather['gust_speed']
            if gust_speed and 'mph' in gust_speed:
                gust_speed = float(gust_speed.split()[0])
            elif gust_speed:
                gust_speed = float(gust_speed)
            else:
                gust_speed = None
            # Parse solar irradiance (W/m2, may include 'W/m2' in string)
            solar_irradiance = weather['solar_irradiance']
            if solar_irradiance and 'W/m2' in solar_irradiance:
                solar_irradiance = float(solar_irradiance.split()[0])
            elif solar_irradiance:
                solar_irradiance = float(solar_irradiance)
            else:
                solar_irradiance = None
        except Exception as e:
            print(f"Error parsing weather data: {e}")
            outdoor_temp = gust_speed = solar_irradiance = None

#        print(f"outdoor_temp = {outdoor_temp}")
#        print(f"gust_speed = {gust_speed}")
#        print(f"solar_irradiance = {solar_irradiance}")

        if outdoor_temp is not None and outdoor_temp > MIN_TEMPERATURE:
            if gust_speed is not None and gust_speed < MAX_GUST_SPEED:
                if solar_irradiance is not None and solar_irradiance > MIN_SOLAR_IRRADIANCE:
                    if (front_angle.is_within_bounds('270d', '360d') or front_angle.is_within_bounds('0d', '90d')): # front
                        blinds_to_lower = 'South'
                    if (front_angle.is_within_bounds('0d', '180d')): # right
                        if len(blinds_to_lower) > 0: blinds_to_lower += ' '
                        blinds_to_lower += 'West'
                    if (front_angle.is_within_bounds('90d', '272d')): # back (skip degrees 270-271 because they are so oblique)
                        if len(blinds_to_lower) > 0: blinds_to_lower += ' '
                        blinds_to_lower += 'North'
                    if (front_angle.is_within_bounds('180d', '360d')): # left
                        if len(blinds_to_lower) > 0: blinds_to_lower += ' '
                        blinds_to_lower += 'East'

set_blinds(blinds_to_lower)

