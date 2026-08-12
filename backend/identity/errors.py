class PinPolicyError(ValueError):
    """A proposed PIN does not satisfy the public policy."""


class InvalidCredentials(ValueError):
    code = "invalid_credentials"

    def __init__(self, message: str = "The employee number or PIN is invalid."):
        super().__init__(message)


class InitialAdminBootstrapRefused(RuntimeError):
    """The one-time zero-account bootstrap precondition is not satisfied."""
