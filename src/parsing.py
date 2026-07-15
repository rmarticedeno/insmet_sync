import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .decodeMessage import decode_message_legacy, get_utc_obs_time
from .vendor.synack.parser import SYNOPParser


logger = logging.getLogger(__name__)

DB_COLUMNS = (
    "obs_time",
    "station_id",
    "aws",
    "air_temperature",
    "air_temperature_flag",
    "minimum_temperature",
    "minimum_temperature_flag",
    "minimum_temperature_period",
    "maximum_temperature",
    "maximum_temperature_flag",
    "maximum_temperature_period",
    "station_pressure",
    "station_pressure_flag",
    "sea_level_pressure",
    "geopotential_surface",
    "geopotential_height",
    "pressure_tendency",
    "pressure_change_3h",
    "pressure_change_24h",
    "dewpoint_temperature",
    "dewpoint_temperature_flag",
    "relative_humidity",
    "relative_humidity_flag",
    "saturation_deficit",
    "heat_index",
    "precipitation_s3",
    "precipitation_s3_trace",
    "precipitation_s3_flag",
    "precipitation_s3_period",
    "precipitation_s1",
    "precipitation_s1_trace",
    "precipitation_s1_flag",
    "precipitation_s1_period",
    "precipitation_24h",
    "precipitation_24h_trace",
    "precipitation_24h_flag",
    "surface_wind_speed",
    "surface_wind_speed_flag",
    "surface_wind_direction_calm",
    "surface_wind_direction",
    "present_weather",
    "past_weather_1",
    "past_weather_2",
    "highest_gust_speed",
    "highest_gust_speed_flag",
    "highest_gust_direction",
    "highest_gust_date",
    "temperature_change",
    "temperature_change_flag",
    "temperature_change_date",
    "evapotranspiration",
    "evapotranspiration_flag",
    "evapotranspiration_type",
    "sunshine",
    "sunshine_flag",
    "sunshine_period",
    "global_solar_radiation",
    "global_solar_radiation_flag",
    "global_solar_radiation_period",
    "ground_state",
    "horizontal_visibility",
    "cloud_cover",
    "cloud_cover_obscured",
    "low_cloud_amount",
    "low_cloud_type",
    "middle_cloud_type",
    "high_cloud_type",
    "lowest_cloud_base_min",
    "lowest_cloud_base_max",
    "tropical_sky_state",
    "low_cloud_drift",
    "middle_cloud_drift",
    "vertical_cloud_genus",
    "vertical_cloud_direction",
    "vertical_cloud_top",
    "cloud_genus_layer_1",
    "cloud_cover_layer_1",
    "cloud_height_layer_1",
    "cloud_genus_layer_2",
    "cloud_cover_layer_2",
    "cloud_height_layer_2",
    "cloud_genus_layer_3",
    "cloud_cover_layer_3",
    "cloud_height_layer_3",
    "cloud_genus_layer_4",
    "cloud_cover_layer_4",
    "cloud_height_layer_4",
    "sea_state",
    "wind_speed",
)


@dataclass
class ParseResult:
    payload: OrderedDict[str, Any]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fallback_fields: dict[str, str] = field(default_factory=dict)
    discrepancies: dict[str, dict[str, Any]] = field(default_factory=dict)
    parser_sources: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


_synop_parser: SYNOPParser | None = None


def _get_synop_parser() -> SYNOPParser:
    global _synop_parser
    if _synop_parser is None:
        _synop_parser = SYNOPParser()
    return _synop_parser


def _blank_payload() -> OrderedDict[str, Any]:
    return OrderedDict((column, None) for column in DB_COLUMNS)


def _ordered_payload(data: dict[str, Any]) -> OrderedDict[str, Any]:
    payload = _blank_payload()
    for key, value in data.items():
        if key in payload:
            payload[key] = value
    return payload


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _cloud_cover_to_code(value: str | None) -> int | None:
    mapping = {
        "Clear": 0,
        "1/8 or less": 1,
        "2/8": 2,
        "3/8": 3,
        "4/8": 4,
        "5/8": 5,
        "6/8": 6,
        "7/8 or more, not overcast": 7,
        "Overcast": 8,
        "Sky obscured": None,
    }
    return mapping.get(value)


def _normalized_obs_time(message: dict[str, Any]) -> str | None:
    day = _nested_get(message, "section_0", "date_location", "day")
    hour = _nested_get(message, "section_0", "date_location", "hour")
    minute = _nested_get(message, "section_1", "enumerated_groups", "time_of_observation", "hour")
    exact_minute = _nested_get(message, "section_1", "enumerated_groups", "time_of_observation", "minute")
    if day is None or hour is None:
        return None

    minute_value = 0
    obs_hour = hour
    if minute is not None:
        obs_hour = minute
        minute_value = exact_minute or 0

    utc_obs_time = get_utc_obs_time(int(day), int(obs_hour), int(minute_value))
    local_time = utc_obs_time + timedelta(hours=-5)
    return local_time.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_synack(message: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    station_id = _nested_get(message, "section_0", "station_info", "station_id")
    if station_id:
        normalized["station_id"] = station_id

    obs_time = _normalized_obs_time(message)
    if obs_time:
        normalized["obs_time"] = obs_time

    staffed = _nested_get(message, "section_1", "wind_visibility_clouds", "misc_data", "is_staffed")
    if staffed is not None:
        normalized["aws"] = not staffed

    air_temperature = _nested_get(message, "section_1", "enumerated_groups", "air_temperature", "temperature_data", "value")
    if air_temperature is not None:
        normalized["air_temperature"] = air_temperature

    dewpoint = _nested_get(message, "section_1", "enumerated_groups", "dew_point_temperature", "temperature_data", "value")
    if dewpoint is not None:
        normalized["dewpoint_temperature"] = dewpoint

    station_pressure = _nested_get(message, "section_1", "enumerated_groups", "station_pressure", "value")
    if station_pressure is not None:
        normalized["station_pressure"] = station_pressure

    sea_level_pressure = _nested_get(message, "section_1", "enumerated_groups", "sea_level_pressure", "value")
    if sea_level_pressure is not None:
        normalized["sea_level_pressure"] = sea_level_pressure

    tendency = _nested_get(message, "section_1", "enumerated_groups", "pressure_tendency", "characteristic_code")
    if tendency is not None:
        normalized["pressure_tendency"] = int(tendency)

    tendency_change = _nested_get(message, "section_1", "enumerated_groups", "pressure_tendency", "amount")
    if tendency_change is not None:
        tendency_code = normalized.get("pressure_tendency")
        normalized["pressure_change_3h"] = -tendency_change if tendency_code and tendency_code > 4 else tendency_change

    pressure_24h = _nested_get(message, "section_3", "section_3_groups", "pressure_change", "pressure_change")
    if pressure_24h is not None:
        normalized["pressure_change_24h"] = pressure_24h

    visibility = _nested_get(message, "section_1", "wind_visibility_clouds", "misc_data", "visibility", "value")
    if visibility is not None:
        normalized["horizontal_visibility"] = int(float(visibility) * 1000)

    cloud_height = _nested_get(message, "section_1", "wind_visibility_clouds", "misc_data", "lowest_cloud_height")
    if isinstance(cloud_height, list) and len(cloud_height) == 2:
        normalized["lowest_cloud_base_min"] = cloud_height[0]
        normalized["lowest_cloud_base_max"] = cloud_height[1]

    wind_speed = _nested_get(message, "section_1", "wind_visibility_clouds", "wind_data", "wind_speed", "speed")
    if wind_speed is not None:
        normalized["surface_wind_speed"] = wind_speed

    wind_degrees = _nested_get(message, "section_1", "wind_visibility_clouds", "wind_data", "wind_direction", "degrees")
    if wind_degrees is not None:
        normalized["surface_wind_direction_calm"] = False
        normalized["surface_wind_direction"] = wind_degrees

    cloud_cover_value = _nested_get(message, "section_1", "wind_visibility_clouds", "wind_data", "cloud_cover")
    if cloud_cover_value is not None:
        normalized["cloud_cover"] = _cloud_cover_to_code(cloud_cover_value)
        normalized["cloud_cover_obscured"] = cloud_cover_value == "Sky obscured"

    present_weather = _nested_get(message, "section_1", "enumerated_groups", "weather_group", "present_weather", "code")
    if present_weather is not None:
        normalized["present_weather"] = present_weather

    past_weather_1 = _nested_get(message, "section_1", "enumerated_groups", "weather_group", "past_weather_1", "code")
    if past_weather_1 is not None:
        normalized["past_weather_1"] = past_weather_1

    past_weather_2 = _nested_get(message, "section_1", "enumerated_groups", "weather_group", "past_weather_2", "code")
    if past_weather_2 is not None:
        normalized["past_weather_2"] = past_weather_2

    low_amount = _nested_get(message, "section_1", "enumerated_groups", "cloud_information", "low_clouds", "amount")
    if low_amount is not None:
        normalized["low_cloud_amount"] = _cloud_cover_to_code(low_amount)
    low_type = _nested_get(message, "section_1", "enumerated_groups", "cloud_information", "low_clouds", "cloud_type", "code")
    if low_type is not None:
        normalized["low_cloud_type"] = int(low_type)
    middle_type = _nested_get(message, "section_1", "enumerated_groups", "cloud_information", "mid_clouds", "cloud_type", "code")
    if middle_type is not None:
        normalized["middle_cloud_type"] = int(middle_type)
    high_type = _nested_get(message, "section_1", "enumerated_groups", "cloud_information", "high_clouds", "cloud_type", "code")
    if high_type is not None:
        normalized["high_cloud_type"] = int(high_type)

    ground_state = _nested_get(message, "section_3", "section_3_groups", "soil", "soil")
    if ground_state is not None:
        normalized["ground_state"] = ground_state

    layer = _nested_get(message, "section_3", "section_3_groups", "cloud_layer_data")
    if isinstance(layer, dict):
        normalized["cloud_genus_layer_1"] = int(layer["cloud_type"])
        normalized["cloud_cover_layer_1"] = int(layer["cloud_amount"])
        normalized["cloud_height_layer_1"] = layer["cloud_height"]

    return normalized


def parse_fm12(raw_message: str) -> ParseResult:
    warnings: list[str] = []
    errors: list[str] = []
    fallback_fields: dict[str, str] = {}
    discrepancies: dict[str, dict[str, Any]] = {}

    try:
        legacy_payload = _ordered_payload(decode_message_legacy(raw_message))
    except Exception as exc:
        logger.exception("Legacy parser failed for message")
        legacy_payload = _blank_payload()
        warnings.append(f"legacy parser failed: {exc}")

    parser_sources = {column: "legacy" for column in DB_COLUMNS}

    synack_message: dict[str, Any] | None = None
    try:
        synack_result = _get_synop_parser().parse(raw_message)
        synack_errors = synack_result.get("errors") or []
        if synack_errors:
            warnings.extend(f"synack: {item}" for item in synack_errors)
        if isinstance(synack_result.get("message"), dict):
            synack_message = synack_result["message"]
    except Exception as exc:
        logger.exception("synack parser failed for message")
        warnings.append(f"synack parser failed: {exc}")

    if synack_message:
        normalized = _normalize_synack(synack_message)
        for field_name, synack_value in normalized.items():
            if field_name not in legacy_payload or synack_value is None:
                continue
            legacy_value = legacy_payload[field_name]
            if legacy_value != synack_value and legacy_value is not None:
                discrepancies[field_name] = {
                    "legacy": legacy_value,
                    "synack": synack_value,
                }
            legacy_payload[field_name] = synack_value
            parser_sources[field_name] = "synack"

    if not legacy_payload.get("station_id") or not legacy_payload.get("obs_time"):
        errors.append("Unable to determine station_id and obs_time from FM-12 message")

    for field_name, source in parser_sources.items():
        if source == "legacy":
            fallback_fields[field_name] = "legacy"

    return ParseResult(
        payload=legacy_payload,
        warnings=warnings,
        errors=errors,
        fallback_fields=fallback_fields,
        discrepancies=discrepancies,
        parser_sources=parser_sources,
    )
