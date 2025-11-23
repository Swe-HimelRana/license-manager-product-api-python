"""
Custom exceptions for License Manager Product API Client
"""


class ApiException(Exception):
    """
    Exception raised for API errors.

    This exception is raised when an API request returns an error response.
    It includes the HTTP status code and any error details from the API.
    """

    def __init__(self, message: str, status_code: int = 0, errors: dict = None):
        """
        Initialize API exception.

        Args:
            message: The exception message
            status_code: The HTTP status code
            errors: Additional error details from the API
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}

    def __str__(self) -> str:
        """
        Return string representation of the exception.

        Returns:
            Formatted exception message with status code if available
        """
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message

    def get_errors(self) -> dict:
        """
        Get additional error details from the API response.

        Returns:
            Dictionary of error details
        """
        return self.errors

    def has_errors(self) -> bool:
        """
        Check if the exception has additional error details.

        Returns:
            True if errors dictionary is not empty
        """
        return bool(self.errors)

