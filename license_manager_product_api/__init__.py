"""
License Manager Product API Client

This package provides a client for interacting with the License Manager Product API.
It supports both Admin and Client product tokens for product-specific operations.
"""

from .client import Client
from .exceptions import ApiException

__all__ = ["Client", "ApiException"]
__version__ = "1.0.0"

