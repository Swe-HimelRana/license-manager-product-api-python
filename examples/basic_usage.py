#!/usr/bin/env python3
"""
Basic usage example for License Manager Product API Client
"""

from license_manager_product_api import Client, ApiException

# Initialize client with a product token (Admin or Client)
client = Client(
    base_url="http://localhost:8000",
    product_token="your-product-token-here",
    hmac_secret="your-hmac-secret-here"  # Optional
)

# Example: Verify license (Client Token)
try:
    result = client.verify_license({
        "key": "XXXX-XXXX-XXXX-XXXX",
    })

    if result.get("is_active"):
        print("License is active!")
        print(f"Status: {result['license']['status']}")
    else:
        print(f"License is not active. Status: {result.get('status')}")
except ApiException as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")

# Example: Activate license (Client Token)
try:
    result = client.activate_license({
        "key": "XXXX-XXXX-XXXX-XXXX",
        "domain": "example.com",
        "hostname": "server-01",
        "machine_id": "MACHINE-123",
        "version": "1.0.0",
    })
    print(f"Activation ID: {result['activation_id']}")
except ApiException as e:
    print(f"API Error: {e.message}")

# Example: Issue license (Admin Token)
try:
    result = client.issue_license({
        "type": "regular",
        "status": "active",
        "expires_at": "2026-12-31",
        "activation_limit": 1,
        "buyer_name": "John Doe",
        "buyer_email": "john@example.com",
    })
    print(f"License key: {result['license']['key']}")
except ApiException as e:
    print(f"API Error: {e.message}")

# Example: Get credit balance (Client Token)
try:
    balance = client.get_credits_balance({
        "key": "XXXX-XXXX-XXXX-XXXX",
    })
    print(f"Total credits: {balance['license']['total_credits']}")
except ApiException as e:
    print(f"API Error: {e.message}")

# Example: Get product updates (Client Token)
try:
    updates = client.get_product_updates("product-uuid")
    print(f"Current version: {updates['current_version']}")
except ApiException as e:
    print(f"API Error: {e.message}")

