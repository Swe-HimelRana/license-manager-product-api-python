"""
License Manager Product API Client

This module provides a client for interacting with the License Manager Product API.
It supports both Admin and Client product tokens for product-specific operations.
Product tokens are scoped to a specific product and automatically determine the product
for API requests, so product_id is not required in most requests.
"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
from requests.exceptions import RequestException

from .exceptions import ApiException


class Client:
    """
    Client for License Manager Product API using product tokens.

    This client provides methods for license management, credits, product resources,
    and other product-specific operations using Admin or Client product tokens.
    When using a product token, product_id is automatically determined from the token.
    """

    def __init__(
        self,
        base_url: str,
        product_token: str,
        hmac_secret: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the Product API client.

        Args:
            base_url: Base URL of the License Manager API
            product_token: Product token for authentication (Admin or Client token)
            hmac_secret: Optional HMAC secret for signature verification
            timeout: Request timeout in seconds
        """
        if not base_url:
            raise ValueError("Base URL is required")
        if not product_token:
            raise ValueError("Product token is required")

        self.base_url = base_url.rstrip("/")
        self.product_token = product_token
        self.hmac_secret = hmac_secret
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "X-Product-Token": self.product_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _normalize_data(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Normalize arguments to support both dictionary and keyword arguments.
        
        Args:
            data: Optional dictionary of data
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary of normalized data (never None, but may be empty)
            
        Examples:
            # Dictionary style
            client.method({"key": "value", "domain": "example.com"})
            
            # Keyword style
            client.method(key="value", domain="example.com")
            
            # Mixed (kwargs override dict values if keys overlap)
            client.method({"key": "value"}, domain="example.com")
        """
        result = {}
        
        # If data is provided as a dict, use it as base
        if isinstance(data, dict):
            result = data.copy()
        
        # Merge kwargs (kwargs will override dict values if keys overlap)
        if kwargs:
            result.update(kwargs)
        
        return result

    # ==================== Admin Token Endpoints ====================

    def issue_license(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Create a new license key for the product associated with your product token.
        Requires Admin Token.

        Args:
            data: Request data containing:
                - type (str, required): License type: regular, extended, trial, lifetime, subscription
                - status (str, optional): Initial status
                - expires_at (str, optional): Expiration date
                - activation_limit (int, optional): Maximum activations
                - buyer_name (str, optional): Buyer name
                - buyer_email (str, optional): Buyer email
                - key (str, optional): Custom license key
                - product_id (str, optional): Product UUID (ignored when using product token)
                - Other optional fields

        Returns:
            Response containing created license information

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/issue", data)

    def change_license_status(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Change the status of a license for the product associated with your product token.
        Requires Admin Token.

        Args:
            data: Request data containing:
                - key (str, required): License key
                - status (str, required): New status
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing updated license information

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/change-status", data)

    def renew_license(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Renew a license for the product associated with your product token.
        Requires Admin Token.

        Args:
            data: Request data containing:
                - key (str, required): License key
                - next_renew_date (str, optional): New expiration date (ISO 8601 or YYYY-MM-DD format)
                - next_renewal_date (str, optional): Alias for next_renew_date (handles typo)
                - additional_days (int, optional): Number of days to add from current expiration date
                - product_id (str, optional): Product UUID (ignored when using product token)
            **kwargs: Can also pass parameters as keyword arguments:
                - key (str, required): License key
                - next_renew_date or next_renewal_date (str, optional): New expiration date
                - additional_days (int, optional): Number of days to add from current expiration
                - product_id (str, optional): Product UUID

        Returns:
            Response containing renewed license information

        Raises:
            ApiException: If the API request fails
            ValueError: If both next_renew_date and additional_days are provided

        Examples:
            # Using additional_days (extends from current expiration date)
            client.renew_license(key='C0F4-DBC1-EA5E-83DC', additional_days=30)
            
            # Using explicit next_renew_date
            client.renew_license(key='C0F4-DBC1-EA5E-83DC', next_renew_date='2025-12-31')
            
            # Using next_renewal_date (typo handling)
            client.renew_license(key='C0F4-DBC1-EA5E-83DC', next_renewal_date='2026-12-31')
            
            # Using dictionary
            client.renew_license({'key': 'C0F4-DBC1-EA5E-83DC', 'additional_days': 30})
        """
        data = self._normalize_data(data, **kwargs)
        
        # Handle typo: next_renewal_date -> next_renew_date
        if 'next_renewal_date' in data and 'next_renew_date' not in data:
            data['next_renew_date'] = data.pop('next_renewal_date')
        
        # Check if both next_renew_date and additional_days are provided
        if 'next_renew_date' in data and 'additional_days' in data:
            raise ValueError("Cannot specify both 'next_renew_date' and 'additional_days'. Use one or the other.")
        
        # If additional_days is provided, calculate next_renew_date from current expiration
        if 'additional_days' in data:
            additional_days = data.pop('additional_days')
            if not isinstance(additional_days, (int, float)) or additional_days < 0:
                raise ValueError("additional_days must be a non-negative number")
            
            # Get current license info to find expiration date
            if 'key' not in data:
                raise ValueError("'key' is required when using 'additional_days'")
            
            try:
                # Fetch current license information
                license_info = self.get_license_info(key=data['key'])
                license_data = license_info.get('license', {})
                current_expires_at = license_data.get('expires_at')
                
                if current_expires_at:
                    # Parse current expiration date and add days
                    current_expires = datetime.fromisoformat(current_expires_at.replace('Z', '+00:00'))
                    # Handle timezone-aware datetime
                    if current_expires.tzinfo:
                        next_renew_date = (current_expires + timedelta(days=int(additional_days))).date()
                    else:
                        next_renew_date = (current_expires + timedelta(days=int(additional_days))).date()
                else:
                    # If no expiration date, add days from today
                    next_renew_date = (datetime.now() + timedelta(days=int(additional_days))).date()
                
                # Format as YYYY-MM-DD (ISO 8601 date format)
                data['next_renew_date'] = next_renew_date.isoformat()
            except (ApiException, KeyError, ValueError) as e:
                # If we can't get license info, fall back to adding from today
                next_renew_date = (datetime.now() + timedelta(days=int(additional_days))).date()
                data['next_renew_date'] = next_renew_date.isoformat()
        
        # Ensure next_renew_date is provided
        if 'next_renew_date' not in data:
            raise ValueError("Either 'next_renew_date' or 'additional_days' must be provided")
        
        return self._post("/api/licenses/renew", data)

    def add_credits(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Add credits to a license for the product associated with your product token.
        Requires Admin Token.

        Args:
            data: Optional dictionary of data, or use keyword arguments
            **kwargs: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - amount (float, required): Credit amount to add
                - description (str, optional): Description
                - metadata (dict, optional): Additional metadata
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing updated license with credits

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/credits/add", data)

    def list_licenses(self) -> Dict[str, Any]:
        """
        Get all licenses created by this product token.
        Requires Admin Token.

        Returns:
            Response containing list of all licenses created by this token with details

        Raises:
            ApiException: If the API request fails
        """
        return self._get("/api/licenses/list")

    # ==================== Client Token Endpoints ====================

    def verify_license(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Verify a license and device.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing license verification result with:
                - is_active (bool): Whether the license is active/verified
                - verified (bool): Whether the license is verified (same as is_active)
                - fingerprint (str): Device fingerprint
                - status (str): License status ('active' if verified, None otherwise)
                - expires_at (str, optional): License expiration date in ISO 8601 format, or None if no expiration
                - created_at (str, optional): License creation date in ISO 8601 format, or None if not available

        Raises:
            ApiException: If the API request fails (except 404 which is handled as verified=false)
        """
        data = self._normalize_data(data, **kwargs)
        
        try:
            response = self._post("/api/licenses/verify", data)
        except ApiException as e:
            # Handle 404 as a valid response (license not found/not verified)
            # The API returns 404 with {"fingerprint": "...", "verified": false}
            if e.status_code == 404:
                try:
                    # The exception message format is "[404] {json_body}" or just the JSON body
                    message = e.message
                    # Remove status code prefix if present (format: "[404] {...}")
                    if message.startswith('[') and ']' in message:
                        json_str = message.split(']', 1)[1].strip()
                    else:
                        json_str = message
                    
                    # Parse the JSON response
                    response = json.loads(json_str)
                    # Ensure it has the expected structure
                    if not isinstance(response, dict) or 'verified' not in response:
                        response = {
                            'verified': False,
                            'fingerprint': response.get('fingerprint') if isinstance(response, dict) else None,
                            'expires_at': response.get('expires_at') if isinstance(response, dict) else None,
                            'created_at': response.get('created_at') if isinstance(response, dict) else None,
                        }
                except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
                    # If we can't parse, return a default unverified response
                    response = {
                        'verified': False,
                        'fingerprint': None,
                        'expires_at': None,
                        'created_at': None,
                    }
            else:
                # Re-raise other exceptions
                raise
        
        # Transform the new minimal response format to match expected structure
        # API now returns: {"fingerprint": "...", "verified": true/false, "expires_at": "...", "created_at": "..."}
        # Transform to: {"is_active": true/false, "verified": true/false, "fingerprint": "...", "status": "active"/None, "expires_at": "...", "created_at": "..."}
        transformed = {
            'verified': response.get('verified', False),
            'is_active': response.get('verified', False),
            'fingerprint': response.get('fingerprint'),
            'status': 'active' if response.get('verified', False) else None,
            'expires_at': response.get('expires_at'),
            'created_at': response.get('created_at'),
        }
        
        return transformed

    def get_license_info(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get detailed license information.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing license information

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        # Only pass params if data dict has values (empty dict is truthy but we want to pass None)
        return self._get("/api/licenses/info", params=data if data else None)

    def activate_license(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Activate a license on a device.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - version (str, optional): Application version
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing activation result

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/activate", data)

    def deactivate_license(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Deactivate a license on a device.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing deactivation result

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/deactivate", data)

    def send_heartbeat(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Send a heartbeat from a device to keep the activation alive.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - version (str, optional): Application version
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing heartbeat acknowledgment

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/heartbeat", data)

    def get_credits_balance(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get credit balance for a license.
        Requires Client Token or Admin Token.

        Args:
            data: Optional dictionary of data, or use keyword arguments
            **kwargs: License key, product_id, or device information (domain, hostname, machine_id, hwid, ip, mac_address)
                     At least one of key or device information is required

        Returns:
            Response containing credit balance

        Raises:
            ApiException: If the API request fails

        Note:
            When using a product token, you can call with just a license key or device information.
            The product is automatically determined from the token if product_id is not provided.
        """
        data = self._normalize_data(data, **kwargs)
        return self._get("/api/licenses/credits/balance", params=data if data else None)

    def get_credits_info(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get credit information for a license.
        Requires Client Token or Admin Token.

        Args:
            data: Optional dictionary of data, or use keyword arguments
            **kwargs: License key, product_id, or device information (domain, hostname, machine_id, hwid, ip, mac_address)
                     At least one of key or device information is required

        Returns:
            Response containing credit information

        Raises:
            ApiException: If the API request fails

        Note:
            When using a product token, you can call with just a license key or device information.
            The product is automatically determined from the token if product_id is not provided.
        """
        data = self._normalize_data(data, **kwargs)
        return self._get("/api/licenses/credits/info", params=data if data else None)

    def reduce_credits(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Reduce credits from a license for the product associated with your product token.
        Requires Client Token.

        Args:
            data: Request data containing either:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - amount (float, required): Amount to reduce (min: 0.01)
                - description (str, optional): Description
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing updated license with remaining credits

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/licenses/credits/reduce", data)

    def get_product_updates(self, data: Optional[Dict[str, Any]] = None, product: str = None, product_id: str = None, key: str = None, **kwargs) -> Dict[str, Any]:
        """
        Get the latest product update information.
        Requires Client Token or Admin Token.

        Args:
            data: Optional dictionary of data, or use keyword arguments
            product: Product UUID or slug (optional if using product token or providing product_id/key).
                    If a license key format (XXXX-XXXX-XXXX-XXXX) is passed, it will be treated as a key.
            product_id: Product UUID or slug (optional, alternative to product parameter)
            key: License key to determine product (optional, alternative to product/product_id)
            **kwargs: Can also pass device information (domain, hostname, machine_id, hwid, ip, mac_address)
                     or other parameters as keyword arguments

        Returns:
            Response containing current version and update information

        Raises:
            ApiException: If the API request fails

        Note:
            When using a product token, you can call without any parameters to get updates
            for the product associated with the token. Alternatively, provide product_id,
            license key, or device information to get updates for a specific product.
            
            If device information is provided (and no product/key is specified), the method
            will first get license info to determine the product, then fetch updates.
        """
        # Normalize data to support both dict and kwargs
        params = self._normalize_data(data, **kwargs)
        
        # Handle legacy positional arguments
        if product:
            # If product looks like a license key (format: XXXX-XXXX-XXXX-XXXX), treat it as a key
            if isinstance(product, str) and self._looks_like_license_key(product):
                params['key'] = product
            else:
                params['product'] = product
        
        if product_id:
            params['product_id'] = product_id
        if key:
            params['key'] = key
        
        # Check if device info is provided but no product/key
        device_fields = ['domain', 'hostname', 'machine_id', 'hwid', 'ip', 'mac_address']
        has_device_info = any(field in params for field in device_fields)
        has_product_or_key = 'product' in params or 'product_id' in params or 'key' in params
        
        # If device info is provided but no product/key, get license info first to determine product
        if has_device_info and not has_product_or_key:
            try:
                license_info = self.get_license_info(params.copy())
                license_data = license_info.get('license', {})
                product_data = license_data.get('product', {})
                if product_data and 'id' in product_data:
                    params['product_id'] = product_data['id']
            except ApiException:
                # If we can't get license info, just pass device info and let API handle it
                pass
        
        # Extract product for URL path if provided
        url_product = params.pop('product', None)
        
        # If product looks like a license key, treat it as a key instead
        if url_product and isinstance(url_product, str) and self._looks_like_license_key(url_product):
            params['key'] = url_product
            url_product = None
        
        if url_product:
            return self._get(f"/api/products/{url_product}/updates", params)
        else:
            return self._get("/api/products/updates", params)
    
    def _looks_like_license_key(self, value: Any) -> bool:
        """
        Check if a value looks like a license key format (XXXX-XXXX-XXXX-XXXX).
        
        Args:
            value: Value to check (must be a string)
            
        Returns:
            True if it looks like a license key format, False otherwise
        """
        import re
        # Only check strings
        if not isinstance(value, str):
            return False
        # License key format: 4 groups of 4 alphanumeric characters separated by hyphens
        pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
        return bool(re.match(pattern, value.upper()))

    def get_product_changelog(self, data: Optional[Dict[str, Any]] = None, product: str = None, product_id: str = None, key: str = None, **kwargs) -> Dict[str, Any]:
        """
        Get product changelog with all versions.
        Requires Client Token or Admin Token.

        Args:
            data: Optional dictionary of data, or use keyword arguments
            product: Product UUID or slug (optional if using product token or providing product_id/key).
                    If a license key format (XXXX-XXXX-XXXX-XXXX) is passed, it will be treated as a key.
            product_id: Product UUID or slug (optional, alternative to product parameter)
            key: License key to determine product (optional, alternative to product/product_id)
            **kwargs: Can also pass device information (domain, hostname, machine_id, hwid, ip, mac_address)
                     or other parameters as keyword arguments

        Returns:
            Response containing product changelog

        Raises:
            ApiException: If the API request fails

        Note:
            When using a product token, you can call without any parameters to get changelog
            for the product associated with the token. Alternatively, provide product_id,
            license key, or device information to get changelog for a specific product.
            
            If device information is provided (and no product/key is specified), the method
            will first get license info to determine the product, then fetch changelog.
        """
        # Normalize data to support both dict and kwargs
        params = self._normalize_data(data, **kwargs)
        
        # Handle legacy positional arguments
        if product:
            # If product looks like a license key (format: XXXX-XXXX-XXXX-XXXX), treat it as a key
            if isinstance(product, str) and self._looks_like_license_key(product):
                params['key'] = product
            else:
                params['product'] = product
        
        if product_id:
            params['product_id'] = product_id
        if key:
            params['key'] = key
        
        # Check if device info is provided but no product/key
        device_fields = ['domain', 'hostname', 'machine_id', 'hwid', 'ip', 'mac_address']
        has_device_info = any(field in params for field in device_fields)
        has_product_or_key = 'product' in params or 'product_id' in params or 'key' in params
        
        # If device info is provided but no product/key, get license info first to determine product
        if has_device_info and not has_product_or_key:
            try:
                license_info = self.get_license_info(params.copy())
                license_data = license_info.get('license', {})
                product_data = license_data.get('product', {})
                if product_data and 'id' in product_data:
                    params['product_id'] = product_data['id']
            except ApiException:
                # If we can't get license info, just pass device info and let API handle it
                pass
        
        # Extract product for URL path if provided
        url_product = params.pop('product', None)
        
        # If product looks like a license key, treat it as a key instead
        if url_product and isinstance(url_product, str) and self._looks_like_license_key(url_product):
            params['key'] = url_product
            url_product = None
        
        if url_product:
            return self._get(f"/api/products/{url_product}/changelog", params)
        else:
            return self._get("/api/products/changelog", params)

    def download_product(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get download URL for a product version.
        Requires Client Token.

        Args:
            data: Request data containing:
                - version (str, required): Version to download
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing download URL and metadata

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/products/download", data)

    def get_secret_files(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get secret files for a product version.
        Requires Client Token.

        Args:
            data: Request data containing:
                - key (str, optional): License key, OR
                - Device information: domain, hostname, machine_id, hwid, ip, mac_address
                  (at least one required if key is not provided)
                - version (str, optional): Version to filter by
                - product_id (str, optional): Product UUID (ignored when using product token)

        Returns:
            Response containing secret files list

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/products/secret-files", data)

    def get_notifications(self, product_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get active notifications.
        Requires Client Token.

        Args:
            product_id: Optional product UUID to filter notifications for a specific product

        Returns:
            Response containing list of notifications

        Raises:
            ApiException: If the API request fails
        """
        params = {"product_id": product_id} if product_id else {}
        return self._get("/api/notifications", params)

    def verify_envato_purchase(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Verify an Envato purchase code and optionally create a license.
        Requires Client Token.

        Args:
            data: Request data containing:
                - code (str, required): Envato purchase code
                - product_id (str, required): Product UUID
                - email (str, required): Buyer email
                - auto_issue (bool, optional): Whether to automatically issue a license

        Returns:
            Response containing purchase verification result and optionally license information

        Raises:
            ApiException: If the API request fails
        """
        data = self._normalize_data(data, **kwargs)
        return self._post("/api/envato/verify", data)

    # ==================== Helper Methods ====================

    def verify_hmac_signature(self, response_body: bytes, signature: str) -> bool:
        """
        Verify HMAC signature from response.

        Args:
            response_body: The raw response body bytes to verify
            signature: The HMAC signature from the X-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.hmac_secret:
            return False

        # Ensure response_body is bytes
        if isinstance(response_body, str):
            response_body = response_body.encode('utf-8')

        expected_signature = hmac.new(
            self.hmac_secret.encode('utf-8'),
            response_body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to the API.

        Args:
            endpoint: The API endpoint path
            params: Query parameters

        Returns:
            Decoded JSON response

        Raises:
            ApiException: If the API request fails
        """
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make POST request to the API.

        Args:
            endpoint: The API endpoint path
            data: Request body data

        Returns:
            Decoded JSON response

        Raises:
            ApiException: If the API request fails
        """
        return self._request("POST", endpoint, json=data)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: The API endpoint path
            params: Query parameters for GET requests
            json: JSON body data for POST requests

        Returns:
            Decoded JSON response

        Raises:
            ApiException: If the API request fails or HMAC verification fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
            )

            # Verify HMAC signature if secret is provided
            # Must verify BEFORE reading response.text to ensure we use raw bytes
            signature = response.headers.get("X-Signature")
            if self.hmac_secret and signature:
                # Use response.content (raw bytes) for verification, not response.text
                if not self.verify_hmac_signature(response.content, signature):
                    raise ApiException("HMAC signature verification failed", 401)

            response.raise_for_status()
            return response.json() if response.text else {}

        except requests.exceptions.HTTPError as e:
            raise self._handle_exception(e)
        except requests.exceptions.RequestException as e:
            raise ApiException(f"Request failed: {str(e)}", 0)

    def _handle_exception(self, exception: RequestException) -> ApiException:
        """
        Handle API exceptions and convert to ApiException.

        Args:
            exception: The requests exception

        Returns:
            ApiException with appropriate message and status code
        """
        if exception.response is not None:
            try:
                data = exception.response.json()
                message = data.get("message", exception.response.text or str(exception))
                errors = data.get("errors", {})
            except (ValueError, json.JSONDecodeError):
                message = exception.response.text or str(exception)
                errors = {}

            return ApiException(message, exception.response.status_code, errors)
        return ApiException(str(exception), 0)

