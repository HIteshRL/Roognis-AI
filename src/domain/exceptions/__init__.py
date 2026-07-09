class DomainException(Exception):
    """Base for all domain exceptions."""

    code: str = "DOMAIN_ERROR"
    status_code: int = 400

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFound(DomainException):
    code = "NOT_FOUND"
    status_code = 404


class DuplicateEntity(DomainException):
    code = "DUPLICATE"
    status_code = 409


class AuthenticationError(DomainException):
    code = "UNAUTHORIZED"
    status_code = 401


class AuthorizationError(DomainException):
    code = "FORBIDDEN"
    status_code = 403


class ValidationError(DomainException):
    code = "VALIDATION_ERROR"
    status_code = 422


class RateLimitExceeded(DomainException):
    code = "RATE_LIMITED"
    status_code = 429


class LLMError(DomainException):
    code = "LLM_ERROR"
    status_code = 502
