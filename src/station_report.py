class StationReport:

    def __init__(self, id, message = None):
        self.message = message
        self.id = id

    def __str__(self):
        if self.message is None:
            return f"{self.id} nil="
        return self.message