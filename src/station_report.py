class StationReport:

    def __init__(self, id, message = None):
        self.message = message
        self.id = id

    def __str__(self):
        if self.message is None:
            return f"{self.id} nil="
        
        pos = self.message.index(self.id)
        message = f"{self.id} {self.message[pos:]}"
        return message