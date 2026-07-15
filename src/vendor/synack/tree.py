from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional
import warnings

from ply.lex import LexToken

from .tables import COMPASS, SPECIAL_CLOUD_HEIGHT, SPECIAL_VISIBILITY

PASCAL_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


def get_name(obj):
    return re.sub(PASCAL_PATTERN, "_", obj.__class__.__name__).lower()


class ASTNode(ABC):
    original: str = ""
    errors: List[str] = None

    def __init__(self, original="", errors=None):
        self.original = original
        self.errors = [] or errors

    def __setattr__(self, name, value):
        if (
            name in getattr(self, "__annotations__", {})
            and isinstance(value, str)
            and not name.startswith("_")
            and name not in {"original", "errors"}
        ):
            data_type = self.__annotations__[name]
            if "/" not in value:
                try:
                    value = data_type(value)
                except ValueError:
                    warnings.warn(f"Value error while converting {value} to {data_type}")
                    value = None
            elif data_type is not str:
                value = None

            if value is not None and hasattr(self, f"convert_{name}"):
                value = getattr(self, f"convert_{name}")(value)
        super().__setattr__(name, value)

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def validate(self) -> List[str]:
        return []


class ErrorNode(ASTNode):
    field: str = ""
    description: str = ""
    name: str = ""

    def __init__(self, name="", field="", description=""):
        super().__init__()
        self.field = field
        self.description = description
        self.name = name

    def to_dict(self):
        return {"field": self.field, "description": self.description}


@dataclass
class StationInfo(ASTNode):
    station_id: str
    message_type: str
    station_type: str
    block_number: str
    station_number: str
    original_message_type: str = ""
    original_station_id: str = ""

    def to_dict(self):
        return {
            "station_id": self.station_id,
            "message_type": self.message_type,
            "station_type": self.station_type,
            "block_number": self.block_number,
            "station_number": self.station_number,
            "original_message_type": self.original_message_type,
            "original_station_id": self.original_station_id,
        }


@dataclass
class DateLocation(ASTNode):
    day: int
    hour: int
    wind_indicator: str
    wind_units: str
    original: str
    errors: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "day": self.day,
            "hour": self.hour,
            "wind_indicator": self.wind_indicator,
            "wind_units": self.wind_units,
            "original": self.original,
        }


@dataclass
class Metadata(ASTNode):
    def __init__(self, *args, name=""):
        super().__init__()
        self.fields = list(args)
        self.name = name

    def to_dict(self):
        res = {}
        for cls in self.fields:
            key = cls.name if hasattr(cls, "name") and cls.name else get_name(cls)
            if not isinstance(cls, dict):
                if not isinstance(cls, ASTNode):
                    value = cls.value if isinstance(cls, LexToken) else cls
                else:
                    value = cls.to_dict()
            else:
                if set(cls.keys()).intersection(res.keys()):
                    warnings.warn(f"{cls} and {res} contain common keys. Can not merge metadata")
                else:
                    res.update(cls)
                continue
            if key in res:
                warnings.warn(f"{key} is already in {self.name}. Merging...")
                if not isinstance(res[key], list):
                    res[key] = [res[key]]
                res[key].append(value)
            else:
                res[key] = value
        return res

    def to_json(self, indent: int = 2):
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def add(self, fld):
        self.fields.insert(0, fld)

    def __str__(self):
        return f"<Metadata({self.name=})>"

    __repr__ = __str__


@dataclass
class MiscData(ASTNode):
    precipitation_included: bool
    is_staffed: bool
    lowest_cloud: str
    lowest_cloud_height: tuple
    visibility: "Visibility"
    original: str

    def to_dict(self):
        return {
            "precipitation_included": self.precipitation_included,
            "is_staffed": self.is_staffed,
            "lowest_cloud": self.lowest_cloud,
            "lowest_cloud_height": self.lowest_cloud_height,
            "visibility": self.visibility.to_dict(),
            "original": self.original,
        }


@dataclass
class WindDirection(ASTNode):
    degrees: int

    def convert_degrees(self, value):
        return value * 10

    def convert_direction(self, value):
        if self.degrees is None:
            return value
        compass_idx = round(self.degrees / 22.5) % 16
        return COMPASS[compass_idx]

    def to_dict(self):
        return {"degrees": self.degrees, "direction": self.convert_direction(self.degrees)}


@dataclass
class WindSpeed(ASTNode):
    speed: int
    unit: str = "m/s"

    def to_dict(self):
        return {"speed": self.speed, "unit": self.unit}


@dataclass
class CloudMovement(ASTNode):
    properties: int
    dir_low_code: int
    dir_low_description: str
    dir_mid_code: int
    dir_mid_description: str
    dir_high_code: int
    dir_high_description: str
    original: str

    def to_dict(self):
        return {
            "properties": self.properties,
            "dir_low_code": self.dir_low_code,
            "dir_low_description": self.dir_low_description,
            "dir_mid_code": self.dir_mid_code,
            "dir_mid_description": self.dir_mid_description,
            "dir_high_code": self.dir_high_code,
            "dir_high_description": self.dir_high_description,
            "original": self.original,
        }


@dataclass
class Visibility(ASTNode):
    value: int
    unit: str = "km"

    def convert_value(self, code):
        if code <= 50:
            return code / 10
        if code <= 55:
            return None
        if code <= 80:
            return code - 50
        if code <= 89:
            return 30 + (code - 80) * 5
        return SPECIAL_VISIBILITY.get(code)

    def to_dict(self):
        return {"value": self.value, "unit": self.unit}


@dataclass
class WindData(ASTNode):
    cloud_cover: str
    wind_direction: WindDirection
    wind_speed: WindSpeed
    original: str

    def to_dict(self):
        return {
            "cloud_cover": self.cloud_cover,
            "wind_direction": self.wind_direction.to_dict(),
            "wind_speed": self.wind_speed.to_dict(),
            "original": self.original,
        }


@dataclass
class TemperatureData(ASTNode):
    sign: int
    value: int
    original: str = ""
    unit: str = "celsius"
    note: str = ""

    def convert_sign(self, value):
        return -1 if value else 1

    def convert_value(self, value):
        if self.sign is None:
            return self.value / 10
        return self.sign * (value / 10)

    def to_dict(self):
        return {
            "sign": self.sign,
            "value": self.value,
            "unit": self.unit,
            "note": self.note,
            "original": self.original,
        }


@dataclass
class PressureData(ASTNode):
    value: float
    unit: str = "hPa"
    original: str = ""
    name: str = ""

    def convert_value(self, value):
        value = value / 10
        return value if value > 99.9 else value + 1000

    def to_dict(self):
        return {"value": self.value, "unit": self.unit, "original": self.original}


@dataclass
class PressureTendency(ASTNode):
    characteristic: str
    characteristic_code: str
    value: int
    unit: str = "hPa"
    original: str = ""

    def convert_value(self, value):
        return value / 10

    def to_dict(self):
        return {
            "characteristic": self.characteristic,
            "characteristic_code": self.characteristic_code,
            "amount": self.value,
            "units": self.unit,
            "original": self.original,
        }


@dataclass
class PrecipitationData(ASTNode):
    amount: float
    duration: int
    duration_description: str
    unit: str = "mm"
    original: str = ""

    def validate_amount(self, value):
        return 0.0 if value in {0, 990} else value / 10

    def to_dict(self):
        return {
            "amount": self.amount,
            "units": "mm",
            "duration": self.duration,
            "duration_description": self.duration_description,
            "original": self.original,
        }


@dataclass
class PrecipitationDaily(ASTNode):
    amount: float
    unit: str = "mm"
    original: str = ""

    def validate_amount(self, value):
        return 0.0 if value in {0, 9999} else value / 10

    def to_dict(self):
        return {"amount": self.amount, "units": "mm", "original": self.original}


@dataclass
class WeatherCode(ASTNode):
    code: int
    description: tuple
    weather_type: str
    name: str = ""

    def to_dict(self):
        return {"code": self.code, "description": self.description, "type": self.weather_type}


@dataclass
class CloudType(ASTNode):
    code: str
    description: str
    level: str

    def to_dict(self):
        return {"code": self.code, "description": self.description, "level": self.level}


@dataclass
class ObservationTime(ASTNode):
    hour: int
    minute: int
    original: str

    def to_dict(self):
        return {"hour": self.hour, "minute": self.minute, "original": self.original}


@dataclass
class Humidity(ASTNode):
    air_humidity: int

    def to_dict(self):
        return {"air_humidity": self.air_humidity}


@dataclass
class SnowDepthData(ASTNode):
    ground_state_snow: str
    ground_state_description: str
    snow_depth: int
    original: str

    def to_dict(self):
        return {
            "ground_state_snow": self.ground_state_snow,
            "ground_state_description": self.ground_state_description,
            "snow_depth": self.snow_depth,
            "snow_depth_unit": "cm",
            "original": self.original,
        }


@dataclass
class CloudLayerData(ASTNode):
    cloud_amount: str
    cloud_amount_description: str
    cloud_type: str
    cloud_type_description: str
    cloud_height: int
    original: str

    def convert_cloud_height(self, height_code):
        if height_code <= 50:
            return height_code * 30
        if 56 <= height_code <= 80:
            return (height_code - 55) * 300 + 1500
        if 81 <= height_code <= 89:
            return (height_code - 80) * 1500 + 8100
        if height_code >= 90:
            return SPECIAL_CLOUD_HEIGHT[height_code]
        return None

    def to_dict(self):
        return {
            "cloud_amount": self.cloud_amount,
            "cloud_amount_description": self.cloud_amount_description,
            "cloud_type": self.cloud_type,
            "cloud_type_description": self.cloud_type_description,
            "cloud_height": self.cloud_height,
            "cloud_height_unit": "meters",
            "original": self.original,
        }


@dataclass
class RadiationData(ASTNode):
    radiation_code: int
    radiation_type: str
    radiation_type_description: str
    value: float
    unit: str
    original: str

    def to_dict(self):
        return {
            "radiation_code": self.radiation_code,
            "radiation_type": self.radiation_type,
            "radiation_type_description": self.radiation_type_description,
            "value": self.value,
            "unit": self.unit,
            "original": self.original,
        }


@dataclass
class Evaporation(ASTNode):
    evaporation_mm: float
    indicator: tuple
    original: str

    def convert_evaporation_mm(self, value):
        return value / 10

    def to_dict(self):
        return {
            "type": "evaporation",
            "evaporation_mm": self.evaporation_mm,
            "indicator": self.indicator,
            "original": self.original,
        }


@dataclass
class SunshineDuration(ASTNode):
    duration_type: str
    duration_hours: float
    radiation_data: Optional[RadiationData] = None
    original: str = ""

    def convert_duration_hours(self, value):
        return value / 10

    def to_dict(self):
        result = {
            "duration_type": self.duration_type,
            "duration_hours": self.duration_hours,
            "original": self.original,
        }
        if self.radiation_data:
            result["radiation_data"] = [val.to_dict() for val in self.radiation_data]
        return result


@dataclass
class Radiation(ASTNode):
    radiation_type: str
    radiation_type_description: str
    period: str
    value: Optional[RadiationData] = None
    unit: str = ""
    original: str = ""

    def to_dict(self):
        return {
            "radiation_type": self.radiation_type,
            "radiation_type_description": self.radiation_type_description,
            "period": self.period,
            "value": [val.to_dict() for val in self.value],
            "unit": self.unit,
            "original": self.original,
        }


@dataclass
class CloudDirection(ASTNode):
    direction_low_cloud: int
    direction_low_cloud_description: str
    direction_mid_cloud: int
    direction_mid_cloud_description: str
    direction_high_cloud: int
    direction_high_cloud_description: str
    original: str = ""

    def to_dict(self):
        return {
            "direction_high_cloud": self.direction_high_cloud,
            "direction_high_cloud_description": self.direction_high_cloud_description,
            "direction_mid_cloud": self.direction_mid_cloud,
            "direction_mid_cloud_description": self.direction_mid_cloud_description,
            "direction_low_cloud": self.direction_low_cloud,
            "direction_low_cloud_description": self.direction_low_cloud_description,
            "original": self.original,
        }


@dataclass
class CloudElevation(ASTNode):
    cloud: int
    cloud_description: str
    direction: int
    direction_description: str
    original: str = ""

    def to_dict(self):
        return {
            "cloud": self.cloud,
            "cloud_description": self.cloud_description,
            "direction": self.direction,
            "direction_description": self.direction_description,
            "original": self.original,
        }


@dataclass
class PressureChange(ASTNode):
    sign: int
    pressure_change: int
    original: str = ""

    def convert_pressure_change(self, value):
        return (value / 10) * self.sign

    def to_dict(self):
        return {"sign": self.sign, "pressure_change": self.pressure_change, "original": self.original}


@dataclass
class TemperatureChange(ASTNode):
    period: int
    sign: int
    temperature_change: int
    original: str = ""

    def convert_sign(self, value):
        if value == 0:
            return 1
        if value == 1:
            return -1
        if value == 9:
            return value
        return None

    def convert_temperature_change(self, value):
        return value if self.sign > 1 else self.sign * value

    def to_dict(self):
        return {
            "period": self.period,
            "sign": self.sign,
            "temperature_change": self.temperature_change,
            "original": self.original,
        }


@dataclass
class Soil(ASTNode):
    soil: int
    soil_description: str
    original: str = ""

    def to_dict(self):
        return {"soil": self.soil, "soil_description": self.soil_description, "original": self.original}


@dataclass
class CloudSpeed(ASTNode):
    cloud_direction: WindDirection
    cloud_speed_code: int
    cloud_speed_description: str
    original: str = ""

    def to_dict(self):
        return {
            "cloud_direction": self.cloud_direction.to_dict(),
            "cloud_speed_code": self.cloud_speed_code,
            "cloud_speed_description": self.cloud_speed_description,
            "original": self.original,
        }
