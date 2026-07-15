import json
import re
import time
import traceback

import ply.lex as lex
import ply.yacc as yacc

try:
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
except Exception:  # pragma: no cover - optional dependency
    metrics = None
    MeterProvider = None
    ConsoleMetricExporter = None
    PeriodicExportingMetricReader = None
    Resource = None

from .builder import (
    build_date_location,
    build_enumerated_group,
    build_misc,
    build_section_3_group,
    build_section_5_group,
    build_station_info,
    build_wind,
)
from .tree import ErrorNode, Metadata

__version__ = "0.3.2"


class _NullCounter:
    def add(self, *_args, **_kwargs):
        return None


class _NullHistogram:
    def record(self, *_args, **_kwargs):
        return None


class ParserState:
    SECTION_0 = 0
    SECTION_1 = 1
    SECTION_3 = 3
    SECTION_3_GROUP_5 = 3.5


class SYNOPParser:
    def __init__(self):
        self.lexer = None
        self.parser = None
        self.state = ParserState.SECTION_0
        self.errors = []
        self.units = {}
        self.length_histogram = _NullHistogram()
        self.parse_counter = _NullCounter()
        self.success_counter = _NullCounter()
        self.error_counter = _NullCounter()
        self.duration_histogram = _NullHistogram()
        self.build_lexer()
        self.build_parser()
        self._init_otel_metrics()

    def _init_otel_metrics(self):
        if not metrics or not MeterProvider or not PeriodicExportingMetricReader or not Resource:
            return
        try:
            resource = Resource.create(attributes={"service.name": "synop_parser"})
            reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
            provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(provider)
            meter = metrics.get_meter(__name__)
            self.parse_counter = meter.create_counter(
                name="synop.parse.count",
                description="Total number of parse calls",
                unit="1",
            )
            self.success_counter = meter.create_counter(
                name="synop.parse.success",
                description="Number of successful parses",
                unit="1",
            )
            self.error_counter = meter.create_counter(
                name="synop.parse.error",
                description="Number of parses that resulted in errors",
                unit="1",
            )
            self.duration_histogram = meter.create_histogram(
                name="synop.parse.duration",
                description="Duration of parse operation in seconds",
                unit="s",
            )
            self.length_histogram = meter.create_histogram(
                name="synop.message.length",
                description="Length of the raw SYNOP message (characters)",
                unit="1",
            )
        except Exception:
            self.length_histogram = _NullHistogram()
            self.parse_counter = _NullCounter()
            self.success_counter = _NullCounter()
            self.error_counter = _NullCounter()
            self.duration_histogram = _NullHistogram()

    tokens = (
        "DIGITS",
        "LETTERS",
        "EQUALS",
        "ZERO_CHUNK",
        "FIVE_CHUNK",
        "DELIMITER_3",
        "DELIMITER_5",
        "RADIATION_EXTRA",
    )

    t_LETTERS = r"AAXX|BBXX"
    t_ignore = " \t"
    t_EQUALS = "="
    t_DELIMITER_5 = "555"

    def t_ZERO_CHUNK(self, t):
        r"00[0-9\/]{2,3}"
        if self.state != ParserState.SECTION_1:
            t.type = "DIGITS"
        return t

    def t_FIVE_CHUNK(self, t):
        r"55[0-9\/]{2,3}"
        if self.state != ParserState.SECTION_3:
            t.type = "DIGITS"
        else:
            self.state = ParserState.SECTION_3_GROUP_5
        return t

    def t_RADIATION_EXTRA(self, t):
        r"[0-5][0-9\/]{3,4}"
        if self.state != ParserState.SECTION_3_GROUP_5:
            t.type = "DIGITS"
        return t

    def t_DELIMITER_3(self, t):
        "333"
        self.state = ParserState.SECTION_3
        return t

    def t_DIGITS(self, t):
        r"[0-9\/]{4,6}"
        if len(self.parser.symstack) == 3:
            self.state = ParserState.SECTION_1
        elif self.state == ParserState.SECTION_3_GROUP_5:
            self.state = ParserState.SECTION_3
        return t

    def t_error(self, t):
        self.errors.append(
            f"Lexer error: Illegal character '{t.value[0]}' at position {t.lexpos}"
        )
        t.lexer.skip(1)

    def build_lexer(self):
        self.lexer = lex.lex(module=self)

    def p_synop_message(self, p):
        """
        synop_message : section_0 EQUALS
                      | section_0 section_1 EQUALS
                      | section_0 section_1 section_3 EQUALS
                      | section_0 section_1 section_3 section_5 EQUALS
                      | section_0
                      | section_0 section_1
                      | section_0 section_1 section_3
                      | section_0 section_1 section_3 section_5
        """
        if len(p) > 4:
            p[0] = Metadata(p[1], p[2], p[3], p[4], name="main")
        elif len(p) > 3:
            p[0] = Metadata(p[1], p[2], p[3], name="main")
        elif len(p) > 2:
            p[0] = Metadata(p[1], p[2], name="main")
        else:
            p[0] = Metadata(p[1], name="main")
        p[0] = p[0].to_dict()

    def p_section_0(self, p):
        """section_0 : LETTERS DIGITS DIGITS"""
        message_type = p[1]
        date_group = p[2]
        station_group = p[3]
        station_data = build_station_info(message_type, station_group)

        if len(date_group) < 5:
            msg = f"Invalid date/time group: {date_group}"
            self.errors.append(msg)
            date_data = ErrorNode(field="date_data", description=msg)
        else:
            date_data = build_date_location(date_group)

        self.units["wind"] = (
            date_data.wind_units if hasattr(date_data, "wind_units") else None
        )
        p[0] = Metadata(date_data, station_data, name="section_0")

    def p_section_1(self, p):
        """
        section_1 : wind_visibility_clouds temperature_pressure_groups
        """
        p[0] = Metadata(p[1], p[2], name="section_1")

    def p_wind_visibility_clouds(self, p):
        """
        wind_visibility_clouds : DIGITS DIGITS ZERO_CHUNK
                               | DIGITS DIGITS
                               | DIGITS ZERO_CHUNK
                               | DIGITS
        """
        group_misc = p[1]
        group_wind = p[2] if len(p) >= 3 else None
        extra_group = p[3] if len(p) == 4 else None

        if len(group_misc) != 5:
            msg = f"Invalid misc group: {group_misc}"
            self.errors.append(msg)
            group_misc_data = ErrorNode(field="misc_group", description=msg)
        else:
            group_misc_data = build_misc(group_misc)

        if not group_wind or len(group_wind) not in {5, 6}:
            msg = f"Invalid wind/visibility group: {group_wind}"
            self.errors.append(msg)
            group_wind_data = ErrorNode(field="wind_group")
        else:
            group_wind_data = build_wind(group_wind, extra_group, wind_unit=self.units["wind"])

        p[0] = Metadata(group_misc_data, group_wind_data, name="wind_visibility_clouds")

    def p_temperature_pressure_groups(self, p):
        """
        temperature_pressure_groups : temperature_pressure_group temperature_pressure_groups
                                    | temperature_pressure_group
        """
        if len(p) == 2:
            p[0] = Metadata(p[1], name="enumerated_groups")
        else:
            p[2].add(p[1])
            p[0] = p[2]

    def p_temperature_pressure_group(self, p):
        """
        temperature_pressure_group : DIGITS
        """
        group = p[1]
        group_type = group[0]
        data = group[1:]

        if len(group) < 4:
            msg = f"Invalid temperature/pressure group: {group}"
            self.errors.append(msg)
            group_enumerated = ErrorNode(
                field=f"enumerated_group_{group_type}",
                description=msg,
            )
        else:
            group_enumerated = build_enumerated_group(group_type, data)
        p[0] = group_enumerated

    def p_section_3(self, p):
        """
        section_3 : DELIMITER_3 section_3_groups
        """
        p[0] = Metadata(p[2], name="section_3")

    def p_section_3_groups(self, p):
        """
        section_3_groups : section_3_group section_3_groups
                         | section_3_group
        """
        if len(p) == 2:
            p[0] = Metadata(p[1], name="section_3_groups")
        else:
            p[2].add(p[1])
            p[0] = p[2]

    def p_section_3_group(self, p):
        """
        section_3_group : DIGITS
                        | FIVE_CHUNK radiation_extra
        """
        group = p[1]
        group_type = group[0]
        data = group[1:]
        extra_data = p[2] if len(p) >= 3 else None
        if len(data) < 4:
            msg = f"Invalid section 3 group: {group}"
            self.errors.append(msg)
            decoded_group = ErrorNode(
                field=f"section_3_group_{group_type}",
                description=msg,
            )
        else:
            decoded_group = build_section_3_group(group_type, data, extra_data=extra_data)
        p[0] = decoded_group

    def p_radiation_extra(self, p):
        """
        radiation_extra : RADIATION_EXTRA radiation_extra
                        | RADIATION_EXTRA
        """
        if len(p) == 2:
            p[0] = [p[1]]
        else:
            p[2].append(p[1])
            p[0] = p[2]

    def p_section_5(self, p):
        """
        section_5 : DELIMITER_5 section_5_groups
        """
        p[0] = Metadata(p[2], name="section_5")

    def p_section_5_groups(self, p):
        """
        section_5_groups : section_5_group section_5_groups
                         | section_5_group
        """
        if len(p) == 2:
            p[0] = Metadata(p[1], name="section_5_groups")
        else:
            p[2].add(p[1])
            p[0] = p[2]

    def p_section_5_group(self, p):
        """
        section_5_group : DIGITS
        """
        group = p[1]
        group_type = group[0]
        group_data = group[1:]
        p[0] = build_section_5_group(group_type, group_data)

    def parse(self, synop_message):
        start_time = time.perf_counter()
        self.length_histogram.record(len(synop_message))
        self.parse_counter.add(1)
        self.errors = []
        clean_message = self._clean_synop_message(synop_message)
        success = False
        try:
            result = self.parser.parse(clean_message, lexer=self.lexer)
            if not result:
                result = {}
            success = len(self.errors) == 0
            return {"errors": self.errors.copy(), "message": result}
        except Exception as exc:
            self.errors.extend(traceback.format_exception(exc))
            self.errors.append(f"Parser error: {str(exc)}")
            return {"errors": self.errors, "message": synop_message}
        finally:
            self.duration_histogram.record(time.perf_counter() - start_time)
            if success:
                self.success_counter.add(1)
            else:
                self.error_counter.add(1)

    def parse_as_json(self, synop_message):
        return json.dumps(self.parse(synop_message), indent=2, default=str)

    def p_section_1_error(self, p):
        """
        section_1 : error temperature_pressure_groups
        """
        p[1] = {"wind_visibility_clouds": None}
        self.p_section_1(p)

    def p_synop_message_error(self, p):
        """
        synop_message : section_0 section_1 error EQUALS
                      | section_0 section_1 error
                      | section_0 error EQUALS
                      | section_0 error
        """
        self.errors.append(
            "Found an error at the end of the statement (probably an unimplemented section). Resynchronizing..."
        )
        self.p_synop_message(p)

    def p_error(self, p):
        if p:
            self.errors.append(
                f"Syntax error at token '{p.value}' (type: {p.type}) at position {p.lexpos}"
            )
            self.parser.errok()
        else:
            self.errors.append("Syntax error at EOF (probably due to a missing `=` character)")

    def build_parser(self):
        self.parser = yacc.yacc(module=self, debug=False, write_tables=False)

    def _clean_synop_message(self, message):
        return re.sub(r"\s+", " ", message.strip())
