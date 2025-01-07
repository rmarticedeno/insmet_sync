from .constans import STATIONID, COUNTRY, TERRESTIALREPORTID, ALL_STATIONS, OMM_STATIONS, NEWMESSAGEHEADER
from .station_report import StationReport

class JointReport:

    def __init__(self, report_number = 123, month_day = "01", hour = "0600"):
        self.omm_stations = self.__get_stations(True)
        self.national_stations = self.__get_stations()
        self.data_type = self.__infer_data_type(hour)
        self.report_number = report_number
        self.month_day = month_day
        self.hour = hour

    def __infer_data_type(self, hour):
        # 00 06 12 18
        if int(hour[:2]) % 6 == 0:
            return "SM"
        # 03 09 15 21
        elif int(hour[:2]) % 3 == 0:
            return "SI"
        else:
            return "SN"

    def __get_stations(self, omm = False):
        predicate = lambda x: omm ^ (x in OMM_STATIONS)
        stations = []
        for x in ALL_STATIONS.keys():
            if predicate(x):
                station = StationReport(x)
                stations.append(station)
        return stations

    def __get_header(self, omm = False):
        value = "20" if omm else "40"
        return f"""{NEWMESSAGEHEADER} {self.report_number}\n{self.data_type}{COUNTRY}{value} {STATIONID} {self.month_day}{self.hour}\n{TERRESTIALREPORTID} {self.month_day}{self.hour[:2]}1"""
    
    def __get_trailer(self):
        return "\n\n\n\nNNNN"

    def __str__(self):
        header1 = self.__get_header(True)
        body1 = "\n".join([str(x) for x in self.omm_stations])
        trailer = self.__get_trailer()
        header2 = self.__get_header()
        body2 = "\n".join([str(x) for x in self.national_stations])

        return f"""{header1}\n{body1}{trailer}\n{header2}\n{body2}{trailer}"""
    
    def update(self, report: StationReport):
        for x in self.omm_stations:
            if x.id == report.id:
                x.message = report.message
                return
        
        for x in self.national_stations:
            if x.id == report.id:
                x.message = report.message