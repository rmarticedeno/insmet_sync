import datetime
from .constans import TERRESTIALREPORTID

class StationReport:

    def __init__(self, id, message = None, day = None, hour = None):
        self.message = message
        self.id = id
        now = datetime.datetime.now(datetime.timezone.utc)
        self.day = now.strftime("%d") if day is None else day
        self.hour = now.strftime("%H") if hour is None else hour

    def __str__(self):
        if self.message is None:
            return f"{self.id} nil="
        return self.message
    
    def get_full_msg(self):
        if self.message is None:
            return str(self)
        return f"{TERRESTIALREPORTID} {self.day}{self.hour}00 {self.message}"