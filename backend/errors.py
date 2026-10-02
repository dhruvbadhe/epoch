"""The one error shape the API returns: {"error": "...", "field": "..."}."""


class ApiError(Exception):
    def __init__(self, message: str, field: str | None = None, status: int = 400):
        super().__init__(message)
        self.message = message
        self.field = field
        self.status = status
