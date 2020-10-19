from .extract import extract

class AndroidExtractError(Exception):
    def __init__(self, message):
        super().__init__(message)
