
class StationReport:

    def __init__(self, id, message):
        self.id = id
        self.message = message

    def __str__(self):
        value = "nil=" if self.message is None else self.message
        return f"{self.id} {value}"
    