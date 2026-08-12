class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int,
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.details = details
