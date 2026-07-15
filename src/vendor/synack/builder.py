from .tables import *
from .tree import *


def build_station_info(message_type: str, station_group: str) -> Metadata:
    station_type = STATIONS.get(message_type)

    if len(station_group) == 5:
        block_number = station_group[0:2]
        station_number = station_group[2:5]
        station_id = f"{block_number}{station_number}"
    else:
        station_id = station_group
        block_number = station_number = "Unknown"

    return StationInfo(
        station_id=station_id,
        message_type=message_type,
        station_type=station_type,
        block_number=block_number,
        station_number=station_number,
        original_message_type=message_type,
        original_station_id=station_group,
    )


def build_date_location(date_group):
    day = date_group[0:2]
    hour = date_group[2:4]
    wind_indicator = date_group[4]
    wind_units = WIND_UNITS.get(wind_indicator)
    return DateLocation(
        day=day,
        hour=hour,
        wind_indicator=wind_indicator,
        wind_units=wind_units,
        original=date_group,
    )


def build_misc(misc_group: str):
    precipitation_included = misc_group[0] in {"0", "1", "2"}
    is_staffed = misc_group[1] in {"1", "2", "3"}
    lowest_cloud = misc_group[2]
    lowest_cloud_height = LOWEST_CLOUD_HEIGHT.get(lowest_cloud)
    visibility = misc_group[3:5]

    return MiscData(
        precipitation_included=precipitation_included,
        is_staffed=is_staffed,
        lowest_cloud=lowest_cloud,
        lowest_cloud_height=lowest_cloud_height,
        visibility=Visibility(visibility),
        original=misc_group,
    )


def build_wind(wind_group, extra_wind_group=None, wind_unit=None):
    cloud_cover_code = wind_group[0]
    wind_dir_code = wind_group[1:3]
    wind_speed_code = wind_group[3:5] if not extra_wind_group else extra_wind_group

    cloud_cover = CLOUD_COVER.get(cloud_cover_code)
    wind_direction = WindDirection(wind_dir_code)
    wind_speed = WindSpeed(wind_speed_code, wind_unit)

    return WindData(
        cloud_cover=cloud_cover,
        wind_direction=wind_direction,
        wind_speed=wind_speed,
        original=wind_group,
    )


def build_enumerated_group(group_type, data):
    if group_type in {"1", "2"}:
        if not data.startswith("29"):
            parsed = _parse_temperature(data)
        else:
            parsed = Humidity(data[2:])
        result = Metadata(parsed, name=ENUMERATED_GROUP[int(group_type) - 1])
    elif group_type in {"3", "4"}:
        result = PressureData(data, original=data, name=ENUMERATED_GROUP[int(group_type) - 1])
    elif group_type == "5":
        result = _parse_pressure_tendency(data)
    elif group_type == "6":
        result = _parse_precipitation(data)
    elif group_type == "7":
        result = _parse_alternative_weather(data)
    elif group_type == "8":
        result = _parse_cloud_details(data)
    elif group_type == "9":
        result = _parse_observation_time(data)
    else:
        result = ErrorNode(
            name=f"enumerated_group_{group_type}",
            description=f"Invalid group type {group_type}",
        )
    return result


def _parse_temperature(data, note=""):
    sign_char = data[0]
    temp_value = data[1:4]
    return TemperatureData(sign_char, temp_value, original=data, note=note)


def _parse_pressure_tendency(data):
    characteristic_code = data[0]
    characteristic = TENDENCY_MAP.get(characteristic_code)
    value = data[1:4]
    return PressureTendency(characteristic, characteristic_code, value, original=data)


def _parse_precipitation(data):
    amount_code = data[0:3]
    duration = data[3]
    duration_description = DURATION_MAP.get(duration)
    return PrecipitationData(amount_code, duration, duration_description, original=data)


def _parse_alternative_weather(data):
    present_weather = data[0:2]
    past_weather_1 = data[2]
    past_weather_2 = data[3]

    return Metadata(
        WeatherCode(present_weather, PRESENT_WEATHER.get(present_weather), "present", name="present_weather"),
        WeatherCode(past_weather_1, PAST_WEATHER.get(past_weather_1), "past", name="past_weather_1"),
        WeatherCode(past_weather_2, PAST_WEATHER.get(past_weather_2), "past", name="past_weather_2"),
        name="weather_group",
    )


def _parse_cloud_details(data):
    low_clouds = data[0]
    cloud_types = data[1:4]
    low_cloud_type = cloud_types[0]
    mid_cloud_type = cloud_types[1]
    high_cloud_type = cloud_types[2]

    return Metadata(
        Metadata({"amount": CLOUD_COVER.get(low_clouds)}, _parse_cloud_type(low_cloud_type, "low"), name="low_clouds"),
        Metadata(_parse_cloud_type(mid_cloud_type, "mid"), name="mid_clouds"),
        Metadata(_parse_cloud_type(high_cloud_type, "high"), name="high_clouds"),
        name="cloud_information",
    )


def _parse_cloud_type(cloud_code, level):
    description = CLOUD_TYPE_MAP.get(level, {}).get(cloud_code, "Unknown cloud type")
    return CloudType(cloud_code, description, level)


def _parse_observation_time(data):
    hour = data[0:2]
    minute = data[2:4] if len(data) >= 4 else 0
    return ObservationTime(hour, minute, data)


def build_section_3_group(group_type, data, extra_data=None):
    if group_type == "0":
        result = _parse_cloud_movement(data)
    elif group_type in {"1", "2"}:
        result = _parse_temperature(data, note="max" if group_type == "1" else "min")
    elif group_type == "3":
        result = _parse_soil(data)
    elif group_type == "4":
        result = _parse_snow_depth(data)
    elif group_type == "5":
        result = _parse_section_3_group_5(data, extra_data)
    elif group_type == "6":
        result = _parse_precipitation(data)
    elif group_type == "7":
        result = PrecipitationDaily(data, original=data)
    elif group_type == "8":
        result = _parse_cloud_layer(data)
    elif group_type == "9":
        result = _parse_special_phenomena(data)
    else:
        result = ErrorNode(
            name=f"section_3_group_{group_type}",
            description=f"Unsupported Section 3 group type: {group_type}",
        )
    return result


def _parse_cloud_movement(data):
    properties = data[0]
    dir_low_code = data[1:2]
    dir_mid_code = data[2:3]
    dir_high_code = data[3:4]

    return CloudMovement(
        properties,
        dir_low_code=dir_low_code,
        dir_low_description=DIRECTION[dir_low_code],
        dir_mid_code=dir_mid_code,
        dir_mid_description=DIRECTION[dir_mid_code],
        dir_high_code=dir_high_code,
        dir_high_description=DIRECTION[dir_high_code],
        original=data,
    )


def _parse_soil(data):
    soil = data[0]
    return Soil(soil, SOIL_STATE.get(soil), original=data)


def _parse_snow_depth(data):
    ground_state_snow = data[0]
    snow_depth = data[1:4]
    return SnowDepthData(
        ground_state_snow,
        GROUND_STATE_SNOW.get(ground_state_snow),
        snow_depth,
        original=data,
    )


def _parse_cloud_layer(data):
    cloud_amount = data[0]
    cloud_type = data[1]
    cloud_height_code = data[2:4]
    return CloudLayerData(
        cloud_amount,
        CLOUD_COVER.get(cloud_amount),
        cloud_type,
        CLOUD_TYPES.get(cloud_type),
        cloud_height_code,
        original=data,
    )


def _parse_section_3_group_5(data, extra_data=None):
    extra_data = extra_data or []
    if data.startswith("4"):
        return _parse_temperature_change(data[1:])
    if data.startswith("53"):
        return _parse_sunshine(data[2:], extra_data, "hourly")
    if data.startswith("54") or data.startswith("55"):
        return _parse_radiation(data, extra_data, "hourly" if data.startswith("54") else "daily")
    if data.startswith("5"):
        return _parse_sunshine(data[1:], extra_data)
    if data.startswith("6"):
        return _parse_cloud_direction(data[1:])
    if data.startswith("7"):
        return _parse_cloud_elevation(data)
    if data.startswith("8"):
        return _parse_pressure_change(data, 1)
    if data.startswith("9"):
        return _parse_pressure_change(data, -1)
    return _parse_evaporation(data)


def _parse_evaporation(data):
    evaporation_mm = data[:3]
    indicator = EVAPORATION_CODES.get(data[3])
    return Evaporation(evaporation_mm=evaporation_mm, indicator=indicator, original=data)


def _parse_temperature_change(data):
    return TemperatureChange(data[0], data[1], TEMPERATURE_CHANGE.get(data[2]))


def _parse_sunshine(data, extra_data, type_="daily"):
    duration = data[: 3 if type_ == "daily" else 2]
    radiation_data = [_parse_radiation_supplementary(extra, type_) for extra in extra_data]
    return SunshineDuration(
        duration_type=type_,
        duration_hours=duration,
        radiation_data=radiation_data,
        original=data,
    )


def _parse_radiation(data, extra_data, type_="daily"):
    radiation_type, description, unit = SPECIAL_RADIATION_TYPES.get(data)
    value = [_parse_radiation_supplementary(extra, type_) for extra in extra_data]
    return Radiation(
        radiation_type=radiation_type,
        radiation_type_description=description,
        period=type_,
        value=value,
        unit=unit,
        original=data,
    )


def _parse_cloud_direction(data):
    dirs = []
    for i in range(3):
        direction = data[i]
        dirs.append(direction)
        if direction in {"0", "9"}:
            dirs.append(SPECIAL_DIRECTION["clouds"].get(direction))
        else:
            dirs.append(DIRECTION.get(direction))
    return CloudDirection(*dirs, original=data)


def _parse_cloud_elevation(data):
    cloud = data[0]
    direction = data[1]
    direction_description = (
        SPECIAL_DIRECTION["phenomena"].get(direction)
        if direction in {"0", "9"}
        else DIRECTION.get(direction)
    )
    return CloudElevation(cloud, CLOUD_TYPES.get(cloud), direction, direction_description, original=data)


def _parse_pressure_change(data, sign):
    return PressureChange(sign=sign, pressure_change=data, original=data)


def _parse_radiation_supplementary(data, period):
    radiation_code = data[0]
    if period == "daily":
        radiation_type, radiation_type_description, unit = RADIATION_TYPES_DAILY.get(radiation_code, (None, None, None))
    else:
        radiation_type, radiation_type_description, unit = RADIATION_TYPES_HOURLY.get(radiation_code, (None, None, None))
    value = data[1:]
    return RadiationData(
        radiation_code,
        radiation_type,
        radiation_type_description,
        value,
        unit,
        original=data,
    )


def _parse_special_phenomena(data):
    return Metadata({"original": data}, name="special_phenomena")


def build_section_5_group(group_type, data):
    if group_type == "1":
        wind_dir_code = data[0:2]
        cloud_speed_code = data[2:4]
        return CloudSpeed(
            cloud_direction=WindDirection(wind_dir_code),
            cloud_speed_code=cloud_speed_code,
            cloud_speed_description=CLOUD_SPEED_TABLE.get(cloud_speed_code),
            original=data,
        )
    if group_type == "2":
        mid_cloud_dir = WindDirection(data[0:3])
        high_cloud_dir = WindDirection(data[3:5])
        return Metadata(
            {
                "mid_cloud_dir": mid_cloud_dir,
                "high_cloud_dir": high_cloud_dir,
                "original": data,
            },
            name="section_5_group_2",
        )
    return ErrorNode(
        name=f"section_5_group_{group_type}",
        description=f"Unsupported Section 5 group type: {group_type}",
    )
