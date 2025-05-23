from pymetdecoder import synop as s
from .metCalc import *
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def decodeMessage(msg):
    result = {}
    air_temperature_missing = False
    dewpoint_temperature_missing = False
    station_pressure_missing = False
    msg_decoded = s.SYNOP().decode(msg)    
    obs_time_day = msg_decoded['obs_time']['day']['value']
    obs_time_hour = msg_decoded['obs_time']['hour']['value']
    if obs_time_hour == 0:
        minimum_temperature_period = 18
        maximum_temperature_period = 12
    elif obs_time_hour == 6:
        minimum_temperature_period = 24
        maximum_temperature_period = 24
    elif obs_time_hour == 12:
        minimum_temperature_period = 12
        maximum_temperature_period = 31
    elif obs_time_hour == 18:
        minimum_temperature_period = 24
        maximum_temperature_period = 12
    else:
        minimum_temperature_period = None
        maximum_temperature_period = None
    try:
        obs_time_hour = msg_decoded['exact_obs_time']['hour']['value']
        obs_time_minute = msg_decoded['exact_obs_time']['minute']['value']
    except Exception:
        obs_time_minute = 0
    utc_time = datetime.now(tz=ZoneInfo("UTC"))
    utc_obs_time = datetime(utc_time.year, utc_time.month, obs_time_day, obs_time_hour, obs_time_minute, 0, 0)
    local_time = utc_obs_time + timedelta(hours=-5)
    if (local_time.month > 5 and local_time.month < 12):
        cyclone_season = True
    else:
        cyclone_season = False
    formatted_datetime = local_time.strftime('%Y-%m-%d %H:%M:%S')
    result['obs_time'] = formatted_datetime
    result['station_id'] = msg_decoded['station_id']['value']
    precipitation_indicator = msg_decoded['precipitation_indicator']['value']
    weather_indicator = msg_decoded['weather_indicator']['value']
    if weather_indicator > 3:
        aws = True
    else:
        aws = False
    result['aws'] = aws

    try:
        air_temperature = msg_decoded['air_temperature']['value']
        result['air_temperature'] = air_temperature
        if (air_temperature < 0 or air_temperature > 40):
            result['air_temperature_flag'] = 6
        else:
            result['air_temperature_flag'] = 0
    except Exception:
        result.update(air_temperature=None, air_temperature_flag=None)
        air_temperature_missing = True

    try:
        minimum_temperature = msg_decoded['minimum_temperature']['value']
        result['minimum_temperature'] = minimum_temperature
        if (minimum_temperature < 0 or minimum_temperature > 40):
            result['minimum_temperature_flag'] = 6
        elif minimum_temperature > air_temperature:
            result['minimum_temperature_flag'] = 7
        else:
            result['minimum_temperature_flag'] = 0
        result['minimum_temperature_period'] = minimum_temperature_period
    except Exception:
        result.update(minimum_temperature=None, minimum_temperature_flag=None, minimum_temperature_period=None)

    try:
        maximum_temperature = msg_decoded['maximum_temperature']['value']
        result['maximum_temperature'] = maximum_temperature
        if (maximum_temperature < 0 or maximum_temperature > 40):
            result['maximum_temperature_flag'] = 6
        elif maximum_temperature < air_temperature:
            result['maximum_temperature_flag'] = 7
        else:
            result['maximum_temperature_flag'] = 0
        result['maximum_temperature_period'] = maximum_temperature_period
    except Exception:
        result.update(maximum_temperature=None, maximum_temperature_flag=None, maximum_temperature_period=None)

    try:
        station_pressure = msg_decoded['station_pressure']['value']
        result['station_pressure'] = station_pressure
        if (station_pressure < 800 or station_pressure > 1100):
            result['station_pressure_flag'] = 6
        else:
            result['station_pressure_flag'] = 0
    except Exception:
        result.update(station_pressure=None, station_pressure_flag=None)
        station_pressure_missing = True

    try:
        result['sea_level_pressure'] = msg_decoded['sea_level_pressure']['value']
        result.update(geopotential_surface=None, geopotential_height=None)
    except Exception:
        result['sea_level_pressure'] = None
        try:
            result['geopotential_surface'] = msg_decoded['geopotential']['surface']['value']
            result['geopotential_height'] = msg_decoded['geopotential']['height']['value']
        except:
            result.update(geopotential_surface=None, geopotential_height=None)

    try:
        pressure_tendency = msg_decoded['pressure_tendency']['tendency']['value']
        result['pressure_tendency'] = pressure_tendency
    except Exception:
        result['pressure_tendency'] = None

    try:
        pressure_change_3h = msg_decoded['pressure_tendency']['change']['value']
        if pressure_tendency > 4:
            pressure_change_3h = -pressure_change_3h
        result['pressure_change_3h'] = pressure_change_3h
    except Exception:
        result['pressure_change_3h'] = None

    try:
        result['pressure_change_24h'] = msg_decoded['pressure_change']['value']
    except Exception:
        result['pressure_change_24h'] = None

    try:
        dewpoint_temperature = msg_decoded['dewpoint_temperature']['value']
        result['dewpoint_temperature'] = dewpoint_temperature
        if dewpoint_temperature > air_temperature:
            result['dewpoint_temperature_flag'] = 7
        else:
            result['dewpoint_temperature_flag'] = 0
    except Exception:
        result.update(dewpoint_temperature=None, dewpoint_temperature_flag=None)
        dewpoint_temperature_missing = True

    if (air_temperature_missing == False and dewpoint_temperature_missing == False):
        if station_pressure_missing == True:
            station_pressure = 1013.2
        saturation_vapor_pressure = find_esat(air_temperature, station_pressure)
        vapor_pressure = find_evapor_tdew(dewpoint_temperature)
        relative_humidity = round(find_hr(vapor_pressure, saturation_vapor_pressure))
        result['relative_humidity'] = round(relative_humidity)
        if (relative_humidity < 10 or relative_humidity > 100):
            result['relative_humidity_flag'] = 6
        else:
            result['relative_humidity_flag'] = 0
        saturation_deficit = round(saturation_vapor_pressure - vapor_pressure, 1)
        result['saturation_deficit'] = saturation_deficit
        heat_index = round(find_heat_index(air_temperature, relative_humidity), 1)
        result['heat_index'] = heat_index
    else:
        result.update(relative_humidity=None, relative_humidity_flag=None, saturation_deficit=None, heat_index=None)

    if precipitation_indicator == 4:
        result.update(precipitation_s3=None, precipitation_s3_trace=None, precipitation_s3_flag=None, precipitation_s3_period=None)
        result.update(precipitation_s1=None, precipitation_s1_trace=None, precipitation_s1_flag=None, precipitation_s1_period=None)
        result.update(precipitation_24h=None, precipitation_24h_trace=None, precipitation_24h_flag=None)
    else:    
        try:
            precipitation_amount_s3 = msg_decoded['precipitation_s3']['amount']['value']
            result['precipitation_s3'] = precipitation_amount_s3
            result['precipitation_s3_trace'] = msg_decoded['precipitation_s3']['amount']['trace']
            if precipitation_amount_s3 > 200:
                result['precipitation_s3_flag'] = 6
            else:
                result['precipitation_s3_flag'] = 0
            result['precipitation_s3_period'] = msg_decoded['precipitation_s3']['time_before_obs']['value']
        except Exception:
            if obs_time_hour % 3 == 0:
                result.update(precipitation_s3=0, precipitation_s3_trace=0, precipitation_s3_flag=0, precipitation_s3_period=3)
            else:
                result.update(precipitation_s3=0, precipitation_s3_trace=0, precipitation_s3_flag=0, precipitation_s3_period=1)
        if obs_time_hour % 6 == 0:
            try:
                precipitation_amount_s1 = msg_decoded['precipitation_s1']['amount']['value']
                result['precipitation_s1'] = precipitation_amount_s1
                result['precipitation_s1_trace'] = msg_decoded['precipitation_s1']['amount']['trace']
                if precipitation_amount_s1 > 400:
                    result['precipitation_s1_flag'] = 6
                else:
                    result['precipitation_s1_flag'] = 0
                result['precipitation_s1_period'] = msg_decoded['precipitation_s1']['time_before_obs']['value']
            except Exception:
                result.update(precipitation_s1=0, precipitation_s1_trace=0, precipitation_s1_flag=0, precipitation_s1_period=6)
            try:
                precipitation_amount_24h = msg_decoded['precipitation_24h']['amount']['value']
                result['precipitation_24h'] = precipitation_amount_24h
                result['precipitation_24h_trace'] = msg_decoded['precipitation_24h']['amount']['trace']
                if precipitation_amount_24h > 500:
                    result['precipitation_24h_flag'] = 6
                else:
                    result['precipitation_24h_flag'] = 0
            except Exception:
                result.update(precipitation_24h=0, precipitation_24h_trace=0, precipitation_24h_flag=0)
        else:
            result.update(precipitation_s1=None, precipitation_s1_trace=None, precipitation_s1_flag=None, precipitation_s1_period=None)
            result.update(precipitation_24h=None, precipitation_24h_trace=None, precipitation_24h_flag=None)

    try:
        surface_wind_speed = msg_decoded['surface_wind']['speed']['value']
        result['surface_wind_speed'] = surface_wind_speed
        if (surface_wind_speed < 0 or surface_wind_speed > 99):
            result['surface_wind_speed_flag'] = 6
        else:
            result['surface_wind_speed_flag'] = 0
    except Exception:
        result.update(surface_wind_speed=None, surface_wind_speed_flag=None)

    try:
        surface_wind_direction_calm = msg_decoded['surface_wind']['direction']['calm']
        result['surface_wind_direction_calm'] = surface_wind_direction_calm
        if surface_wind_direction_calm:
            result['surface_wind_direction'] = None
        else:
            result['surface_wind_direction'] = msg_decoded['surface_wind']['direction']['value']
    except Exception:
        result.update(surface_wind_direction_calm=None, surface_wind_direction=None)

    try:
        result['present_weather'] = msg_decoded['present_weather']['value']
    except Exception:
        result['present_weather'] = None
    try:
        result['past_weather_1'] = msg_decoded['past_weather'][0]['value']
    except Exception:
        result['past_weather_1'] = None
    try:
        result['past_weather_2'] = msg_decoded['past_weather'][1]['value']
    except Exception:
        result['past_weather_2'] = None

    try:
        highest_gust_speed = msg_decoded['highest_gust'][0]['speed']['value']
        result['highest_gust_speed'] = highest_gust_speed
        if highest_gust_speed > 99:
            result['highest_gust_speed_flag'] = 6            
        elif (highest_gust_speed < surface_wind_speed):
            result['highest_gust_speed_flag'] = 7
        else:
            result['highest_gust_speed_flag'] = 0
            try:
                highest_gust_direction_position = msg.rindex('915')
                if highest_gust_direction_position > msg.rindex(' 333 '):
                    highest_gust_direction_group = msg[highest_gust_direction_position:highest_gust_direction_position + 6]
                    highest_gust_direction = 10 * int(highest_gust_direction_group[4:6])
                    result['highest_gust_direction'] = highest_gust_direction
                else:
                    result['highest_gust_direction'] = None
            except Exception:
                result['highest_gust_direction'] = None
            try:    # este grupo no está implementado en el pymetdecoder
                highest_gust_position = msg.rindex('904')
                if highest_gust_position > msg.rindex(' 333 '):
                    highest_gust_group = msg[highest_gust_position:highest_gust_position + 6]
                    highest_gust_time = highest_gust_group[4:6]
                    highest_gust_time = 6 * int(highest_gust_time)          # minutos antes de la hora nominal de la racha máxima
                    highest_gust_date = local_time + timedelta(minutes=-highest_gust_time)
                    formatted_highest_gust_date = highest_gust_date.strftime('%Y-%m-%d %H:%M:%S')
                    result['highest_gust_date'] = formatted_highest_gust_date
                else:
                    result['highest_gust_date'] = None    
            except ValueError:
                result['highest_gust_date'] = None
    except Exception:
        result.update(highest_gust_speed=None, highest_gust_speed_flag=None, highest_gust_direction=None, highest_gust_date=None)

    try:
        result['temperature_change'] = msg_decoded['temperature_change']['change']['value']
        result['temperature_change_flag'] = 0
        temperature_change_time = msg_decoded['temperature_change']['time_before_obs']['value']
        temperature_change_time = local_time + timedelta(hours=-temperature_change_time)
        formatted_temperature_change_date = temperature_change_time.strftime('%Y-%m-%d %H:%M:%S')
        result['temperature_change_date'] = formatted_temperature_change_date
    except Exception:
        result.update(temperature_change=None, temperature_change_flag=None, temperature_change_date=None)

    try:
        result['evapotranspiration'] = msg_decoded['evapotranspiration']['amount']['value']
        result['evapotranspiration_flag'] = 0        
        result['evapotranspiration_type'] = msg_decoded['evapotranspiration']['type']['value']
    except Exception:
        result.update(evapotranspiration=None, evapotranspiration_flag=None, evapotranspiration_type=None)

    try:
        result['sunshine'] = msg_decoded['sunshine']['amount']['value']
        result['sunshine_flag'] = 0        
        result['sunshine_period'] = msg_decoded['sunshine']['duration']['value']
    except Exception:
        result.update(sunshine=None, sunshine_flag=None, sunshine_period=None)

    try:
        result['global_solar_radiation'] = msg_decoded['radiation']['global_solar']['value']
        result['global_solar_radiation_flag'] = 0        
        result['global_solar_radiation_period'] = msg_decoded['radiation']['time_before_obs']['value']
    except Exception:
        result.update(global_solar_radiation=None, global_solar_radiation_flag=None, global_solar_radiation_period=None)

    try:
        result['ground_state'] = msg_decoded['ground_state']['state']['value']
    except Exception:
        result['ground_state'] = None

    try:
        result['horizontal_visibility'] = msg_decoded['visibility']['value']
    except Exception:
        result['horizontal_visibility'] = None

    try:
        if msg_decoded['cloud_cover']['obscured']:
            result.update(cloud_cover=None, cloud_cover_obscured=True)
        else:    
            result.update(cloud_cover=msg_decoded['cloud_cover']['value'], cloud_cover_obscured=False)
    except Exception:
        result.update(cloud_cover=None, cloud_cover_obscured=None)

    try:
        result['low_cloud_amount'] = msg_decoded['cloud_types']['low_cloud_amount']['value']
        low_cloud_type = msg_decoded['cloud_types']['low_cloud_type']['value']
        result['low_cloud_type'] = low_cloud_type
        middle_cloud_type = msg_decoded['cloud_types']['middle_cloud_type']['value']
        result['middle_cloud_type'] = middle_cloud_type
        high_cloud_type = msg_decoded['cloud_types']['high_cloud_type']['value']
        result['high_cloud_type'] = high_cloud_type        
    except Exception:
        result.update(low_cloud_amount=None, low_cloud_type=None, middle_cloud_type=None, high_cloud_type=None)

    try:
        result['lowest_cloud_base_min'] = msg_decoded['lowest_cloud_base']['min']
        result['lowest_cloud_base_max'] = msg_decoded['lowest_cloud_base']['max']
    except Exception:
        result.update(lowest_cloud_base_min=None, lowest_cloud_base_max=None)

    if cyclone_season:
        try:
            result['tropical_sky_state'] = msg_decoded['tropical_sky_state']['value']
        except Exception:
            result['tropical_sky_state'] = None
        try:
            if msg_decoded['tropical_cloud_drift_direction']['low']['isCalmOrStationary']:
                if low_cloud_type == 0:
                    result['low_cloud_drift'] = 'Sin nubes'
                else:
                    result['low_cloud_drift'] = 'Estacionario'
            elif msg_decoded['tropical_cloud_drift_direction']['low']['allDirections']:
                result['low_cloud_drift'] = 'Desconocida'
            else:
                result['low_cloud_drift'] = msg_decoded['tropical_cloud_drift_direction']['low']['value']

            if msg_decoded['tropical_cloud_drift_direction']['middle']['isCalmOrStationary']:
                if middle_cloud_type == 0:
                    result['middle_cloud_drift'] = 'Sin nubes'
                else:
                    result['middle_cloud_drift'] = 'Estacionario'
            elif msg_decoded['tropical_cloud_drift_direction']['middle']['allDirections']:
                result['middle_cloud_drift'] = 'Desconocida'
            else:
                result['middle_cloud_drift'] = msg_decoded['tropical_cloud_drift_direction']['middle']['value']

            if msg_decoded['tropical_cloud_drift_direction']['high']['isCalmOrStationary']:
                if high_cloud_type == 0:
                    result['high_cloud_drift'] = 'Sin nubes'
                else:
                    result['high_cloud_drift'] = 'Estacionario'
            elif msg_decoded['tropical_cloud_drift_direction']['high']['allDirections']:
                result['high_cloud_drift'] = 'Desconocida'
            else:
                result['high_cloud_drift'] = msg_decoded['tropical_cloud_drift_direction']['high']['value']

        except Exception:
            result.update(low_cloud_drift=None, middle_cloud_drift=None, high_cloud_type=None)
    else:

        try:
            if msg_decoded['cloud_drift_direction']['low']['isCalmOrStationary']:
                if low_cloud_type == 0:
                    result['low_cloud_drift'] = 'Sin nubes'
                else:
                    result['low_cloud_drift'] = 'Estacionario'
            elif msg_decoded['cloud_drift_direction']['low']['allDirections']:
                result['low_cloud_drift'] = 'Desconocida'
            else:
                result['low_cloud_drift'] = msg_decoded['cloud_drift_direction']['low']['value']

            if msg_decoded['cloud_drift_direction']['middle']['isCalmOrStationary']:
                if middle_cloud_type == 0:
                    result['middle_cloud_drift'] = 'Sin nubes'
                else:
                    result['middle_cloud_drift'] = 'Estacionario'
            elif msg_decoded['cloud_drift_direction']['middle']['allDirections']:
                result['middle_cloud_drift'] = 'Desconocida'
            else:
                result['middle_cloud_drift'] = msg_decoded['cloud_drift_direction']['middle']['value']

            if msg_decoded['cloud_drift_direction']['high']['isCalmOrStationary']:
                if high_cloud_type == 0:
                    result['high_cloud_drift'] = 'Sin nubes'
                else:
                    result['high_cloud_drift'] = 'Estacionario'
            elif msg_decoded['cloud_drift_direction']['high']['allDirections']:
                result['high_cloud_drift'] = 'Desconocida'
            else:
                result['high_cloud_drift'] = msg_decoded['cloud_drift_direction']['high']['value']

        except Exception:
            result.update(low_cloud_drift=None, middle_cloud_drift=None, high_cloud_type=None)


    try:
        result['vertical_cloud_genus'] = msg_decoded['cloud_elevation']['genus']['value']
        if msg_decoded['cloud_elevation']['direction']['isCalmOrStationary']:
            result['vertical_cloud_direction'] = 'En la estación'
        elif msg_decoded['cloud_elevation']['direction']['allDirections']:
            result['vertical_cloud_direction'] = 'Todas las direcciones'
        else:
            result['vertical_cloud_direction'] = msg_decoded['cloud_elevation']['direction']['value']
        if msg_decoded['cloud_elevation']['elevation']['visible']:   
            result['vertical_cloud_top'] = msg_decoded['cloud_elevation']['elevation']['value']
        else:
            result['vertical_cloud_top'] = 'La cima no se ve'    
    except Exception:
        result.update(vertical_cloud_genus=None, vertical_cloud_direction=None, vertical_cloud_top=None)
    
    try:
        result['cloud_genus_layer_1'] = msg_decoded['cloud_layer'][0]['cloud_genus']['value']
        result['cloud_cover_layer_1'] = msg_decoded['cloud_layer'][0]['cloud_cover']['value']
        try:
            result['cloud_height_layer_1'] = msg_decoded['cloud_layer'][0]['cloud_height']['value']
        except Exception:
            result['cloud_height_layer_1'] = 'Desconocida'
    except Exception:
        result.update(cloud_genus_layer_1=None, cloud_cover_layer_1=None, cloud_height_layer_1=None)

    try:
        result['cloud_genus_layer_2'] = msg_decoded['cloud_layer'][1]['cloud_genus']['value']
        result['cloud_cover_layer_2'] = msg_decoded['cloud_layer'][1]['cloud_cover']['value']
        try:
            result['cloud_height_layer_2'] = msg_decoded['cloud_layer'][1]['cloud_height']['value']
        except Exception:
            result['cloud_height_layer_2'] = 'Desconocida'
    except Exception:
        result.update(cloud_genus_layer_2=None, cloud_cover_layer_2=None, cloud_height_layer_2=None)

    try:
        result['cloud_genus_layer_3'] = msg_decoded['cloud_layer'][2]['cloud_genus']['value']
        result['cloud_cover_layer_3'] = msg_decoded['cloud_layer'][2]['cloud_cover']['value']
        try:
            result['cloud_height_layer_3'] = msg_decoded['cloud_layer'][2]['cloud_height']['value']
        except Exception:
            result['cloud_height_layer_3'] = 'Desconocida'
    except Exception:
        result.update(cloud_genus_layer_3=None, cloud_cover_layer_3=None, cloud_height_layer_3=None)

    try:
        result['cloud_genus_layer_4'] = msg_decoded['cloud_layer'][3]['cloud_genus']['value']
        result['cloud_cover_layer_4'] = msg_decoded['cloud_layer'][3]['cloud_cover']['value']
        try:
            result['cloud_height_layer_4'] = msg_decoded['cloud_layer'][3]['cloud_height']['value']
        except Exception:
            result['cloud_height_layer_4'] = 'Desconocida'
    except Exception:
        result.update(cloud_genus_layer_4=None, cloud_cover_layer_4=None, cloud_height_layer_4=None)

    try:    # este grupo no está decodificado por el pymetdecoder
        sea_state_position = msg.rindex('920')  #  wind_speed ≤ 9 Beaufort
        if sea_state_position > msg.rindex(' 333 '):
            sea_state_group = msg[sea_state_position:sea_state_position + 6]
            result['sea_state'] = sea_state_group[3:4]
            result['wind_speed'] = sea_state_group[4:5]
        else:
            result.update(sea_state=None, wind_speed=None)
    except ValueError:
        try:
            sea_state_position = msg.rindex('921')  #  wind_speed > 9 Beaufort
            if sea_state_position > msg.rindex(' 333 '):
                sea_state_group = msg[sea_state_position:sea_state_position + 6]
                result['sea_state'] = sea_state_group[3:4]
                result['wind_speed'] = 10 + int(sea_state_group[4:5])
            else:
                result.update(sea_state=None, wind_speed=None)
        except ValueError:
            result.update(sea_state=None, wind_speed=None)
 
    return(result)