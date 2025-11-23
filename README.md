# License Manager Product API Client (Python)

Python client library for interacting with the License Manager Product API using product tokens.

## Quick Start

```python
from license_manager_product_api import Client, ApiException

# Initialize client with a product token
client = Client(
    base_url="https://your-license-manager.com",
    product_token="your-product-token",  # Admin or Client token
    hmac_secret="your-hmac-secret"  # Optional, for signature verification
)
```

**Note:** When using a product token, `product_id` is automatically determined from the token and is not required in most API requests.

## Usage

### Flexible Parameter Passing

All methods support both dictionary and keyword argument styles:

```python
# Dictionary style
result = client.verify_license({
    "domain": "example.com",
    "hostname": "server-01",
    "machine_id": "MACHINE-123"
})

# Keyword style
result = client.verify_license(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

# Mixed (kwargs override dict values)
result = client.verify_license(
    {"domain": "example.com"},
    hostname="server-01"
)
```

---

## Admin Token Endpoints

Admin tokens can issue licenses, change status, renew, and create credits.

### Issue License

Create a new license key for your product.

```python
try:
    result = client.issue_license(
        type="regular",
        status="active",
        expires_at="2026-12-31",
        activation_limit=1,
        buyer_name="John Doe",
        buyer_email="john@example.com"
    )
    
    print(f"License key: {result['license']['key']}")
    print(f"Status: {result['license']['status']}")
except ApiException as e:
    print(f"Error: {e.message} (Status: {e.status_code})")
```

**Available license types:** `regular`, `extended`, `trial`, `lifetime`, `subscription`

### Change License Status

Update the status of a license.

```python
result = client.change_license_status(
    key="C0F4-DBC1-EA5E-83DC",
    status="active"  # or "inactive", "suspended", "revoked", "expired"
)

print(f"License status updated: {result['license']['status']}")
```

### Renew License

Renew a license by extending its expiration date.

```python
# Option 1: Extend by additional days from current expiration
result = client.renew_license(
    key="C0F4-DBC1-EA5E-83DC",
    additional_days=30  # Adds 30 days to current expiration date
)

# Option 2: Set explicit expiration date
result = client.renew_license(
    key="C0F4-DBC1-EA5E-83DC",
    next_renew_date="2026-12-31"
)

# Option 3: Using next_renewal_date (typo handling)
result = client.renew_license(
    key="C0F4-DBC1-EA5E-83DC",
    next_renewal_date="2026-12-31"
)

print(f"New expiration date: {result['license']['expires_at']}")
```

**Note:** When using `additional_days`, the method automatically fetches the current license expiration date and extends it by the specified number of days.

### Add Credits

Add credits to a license.

```python
# Using license key
result = client.add_credits(
    key="C0F4-DBC1-EA5E-83DC",
    amount=100.50,
    description="Credit allocation"
)

# Using device information
result = client.add_credits(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123",
    amount=50.0,
    description="Credit allocation"
)

print(f"Total credits: {result['license']['total_credits']}")
```

### List All Licenses

Get all licenses created by this product token.

```python
result = client.list_licenses()

print(f"Total licenses: {result['total']}")
print(f"Quota: {result['quota']['created']} / {result['quota']['limit']}")
print(f"Remaining: {result['quota']['remaining']}")

for license in result['licenses']:
    print(f"Key: {license['key']}")
    print(f"Status: {license['status']}")
    print(f"Type: {license['type']}")
    print(f"Expires: {license['expires_at']}")
    print("---")
```

---

## Client Token Endpoints

Client tokens can verify licenses, activate/deactivate devices, send heartbeats, get license info, access product resources, get notifications, verify Envato purchases, and manage credits.

### Verify License

Verify a license and device. Returns verification status, fingerprint, expiration date, and creation date.

```python
# Using license key
result = client.verify_license(key="C0F4-DBC1-EA5E-83DC")

# Using device information
result = client.verify_license(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123",
    version="1.0.0"
)

# Check verification result
if result.get("verified"):
    print("License is active!")
    print(f"Fingerprint: {result['fingerprint']}")
    print(f"Expires at: {result['expires_at']}")
    print(f"Created at: {result['created_at']}")
    print(f"Status: {result['status']}")
else:
    print("License verification failed")
```

**Response includes:**
- `verified` (bool): Whether the license is verified
- `is_active` (bool): Whether the license is active (same as verified)
- `fingerprint` (str): Device fingerprint
- `status` (str): License status ('active' if verified, None otherwise)
- `expires_at` (str): License expiration date in ISO 8601 format, or None
- `created_at` (str): License creation date in ISO 8601 format, or None

### Get License Info

Get detailed license information.

```python
# Using license key
info = client.get_license_info(key="C0F4-DBC1-EA5E-83DC")

# Using device information
info = client.get_license_info(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

license = info['license']
print(f"Key: {license['key']}")
print(f"Status: {license['status']}")
print(f"Type: {license['type']}")
print(f"Expires: {license['expires_at']}")
print(f"Activation Limit: {license['activation_limit']}")
print(f"Activations: {license['activations_count']}")
print(f"Buyer: {license['buyer_name']} ({license['buyer_email']})")
```

### Activate License

Activate a license on a device.

```python
result = client.activate_license(
    key="C0F4-DBC1-EA5E-83DC",
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123",
    version="1.0.0"
)

print(f"Activation ID: {result['activation_id']}")
print(f"Fingerprint: {result['fingerprint']}")
```

### Deactivate License

Deactivate a license on a device.

```python
# Using device information
result = client.deactivate_license(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

# Using license key and device info
result = client.deactivate_license(
    key="C0F4-DBC1-EA5E-83DC",
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

print(f"Deactivated: {result.get('deactivated', False)}")
```

### Send Heartbeat

Send a heartbeat from a device to keep the activation alive.

```python
result = client.send_heartbeat(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123",
    version="1.0.0"
)

print(f"Last check-in: {result['last_check_in_at']}")
```

### Manage Credits

#### Get Credit Balance

```python
# Using license key
balance = client.get_credits_balance(key="C0F4-DBC1-EA5E-83DC")

# Using device information
balance = client.get_credits_balance(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

print(f"Total credits: {balance['license']['total_credits']}")
print(f"Available credits: {balance['license']['available_credits']}")
```

#### Get Credit Info

```python
# Using license key
info = client.get_credits_info(key="C0F4-DBC1-EA5E-83DC")

# Using device information
info = client.get_credits_info(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123"
)

print(f"Total credits: {info['license']['total_credits']}")
print(f"Available: {info['license']['available_credits']}")
print(f"Transactions: {len(info['transactions'])}")
```

#### Reduce Credits

```python
# Using license key
result = client.reduce_credits(
    key="C0F4-DBC1-EA5E-83DC",
    amount=25.50,
    description="Credit deduction"
)

# Using device information
result = client.reduce_credits(
    domain="example.com",
    hostname="server-01",
    machine_id="MACHINE-123",
    amount=25.50,
    description="Credit deduction"
)

print(f"Remaining credits: {result['license']['available_credits']}")
```

### Product Resources

#### Get Product Updates

```python
# Using product token - no parameters needed
updates = client.get_product_updates()
print(f"Current version: {updates['current_version']}")
print(f"Latest version: {updates['latest_version']}")

# Or specify product explicitly
updates = client.get_product_updates(product="product-uuid")
updates = client.get_product_updates(product_id="product-uuid")
updates = client.get_product_updates(key="C0F4-DBC1-EA5E-83DC")
```

#### Get Product Changelog

```python
# Using product token - no parameters needed
changelog = client.get_product_changelog()

# Or specify product explicitly
changelog = client.get_product_changelog(product="product-uuid")
changelog = client.get_product_changelog(product_id="product-uuid")
changelog = client.get_product_changelog(key="C0F4-DBC1-EA5E-83DC")

for version in changelog['versions']:
    print(f"Version {version['version']}: {version['changelog']}")
```

#### Download Product

Get download URL for a product version.

```python
download = client.download_product(
    key="C0F4-DBC1-EA5E-83DC",
    version="1.0.0"
)

print(f"Download URL: {download['download_url']}")
print(f"File size: {download['file_size']}")
print(f"Checksum: {download['checksum']}")
```

#### Get Secret Files

Get secret files for a product version.

```python
secret_files = client.get_secret_files(
    key="C0F4-DBC1-EA5E-83DC",
    version="1.0.0"  # Optional
)

for file in secret_files['files']:
    print(f"File: {file['name']}")
    print(f"URL: {file['download_url']}")
```

### Notifications

Get active notifications.

```python
# Get all notifications
notifications = client.get_notifications()

# Get notifications for specific product
notifications = client.get_notifications(product_id="product-uuid")

for notification in notifications['notifications']:
    print(f"Title: {notification['title']}")
    print(f"Message: {notification['message']}")
    print(f"Type: {notification['type']}")
```

### Verify Envato Purchase

Verify an Envato/CodeCanyon purchase code and optionally create a license.

```python
result = client.verify_envato_purchase(
    code="purchase-code-here",
    product_id="product-uuid",
    email="buyer@example.com",
    auto_issue=True  # Automatically create license if verified
)

if result.get("ok"):
    print("Purchase verified")
    if "license" in result:
        print(f"License key: {result['license']['key']}")
        print(f"License status: {result['license']['status']}")
```

---

## Error Handling

All API methods raise `ApiException` on errors:

```python
from license_manager_product_api import Client, ApiException

try:
    result = client.verify_license(key="INVALID-KEY")
except ApiException as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    if e.errors:
        print(f"Validation Errors: {e.errors}")
```

**Note:** The `verify_license` method handles 404 responses gracefully and returns `verified: False` instead of raising an exception.

---

## HMAC Signature Verification

If you provide an HMAC secret, the client will automatically verify response signatures:

```python
client = Client(
    base_url="https://your-license-manager.com",
    product_token="your-product-token",
    hmac_secret="your-hmac-secret"  # Enables automatic signature verification
)
```

When HMAC verification is enabled, the client will:
- Automatically verify the `X-Signature` header on all responses
- Raise an `ApiException` if signature verification fails

---

## Product Tokens

Product tokens are scoped to a specific product and are created in Settings → Product Tokens. There are two types:

### Admin Token
- Issue licenses
- Change license status
- Renew licenses
- Add credits
- List all licenses created by the token

### Client Token
- Verify licenses
- Get license information
- Activate/deactivate devices
- Send heartbeats
- Access product resources (updates, changelog, downloads, secret files)
- Get notifications
- Verify Envato purchases
- Manage credits (balance, info, reduce)

**Important:** When using a product token, the `product_id` parameter is automatically determined from the token and is not required in API requests.

---

## Complete Example

```python
from license_manager_product_api import Client, ApiException

# Initialize client
client = Client(
    base_url="https://your-license-manager.com",
    product_token="your-client-token",
    hmac_secret="your-hmac-secret"
)

# Verify license
try:
    result = client.verify_license(
        domain="example.com",
        hostname="server-01",
        machine_id="MACHINE-123",
        version="1.0.0"
    )
    
    if result['verified']:
        print(f"License verified! Expires: {result['expires_at']}")
        
        # Activate if not already activated
        activation = client.activate_license(
            domain="example.com",
            hostname="server-01",
            machine_id="MACHINE-123",
            version="1.0.0"
        )
        print(f"Activated with fingerprint: {activation['fingerprint']}")
        
        # Get license info
        info = client.get_license_info(
            domain="example.com",
            hostname="server-01",
            machine_id="MACHINE-123"
        )
        print(f"License type: {info['license']['type']}")
        print(f"Activation limit: {info['license']['activation_limit']}")
        
        # Check for updates
        updates = client.get_product_updates()
        if updates['has_update']:
            print(f"Update available: {updates['latest_version']}")
            
except ApiException as e:
    print(f"Error: {e.message} (Status: {e.status_code})")
```

---

## Method Reference

### Admin Token Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `issue_license(data)` | Create a new license | `type`, `status`, `expires_at`, `activation_limit`, `buyer_name`, `buyer_email`, etc. |
| `change_license_status(data)` | Change license status | `key`, `status` |
| `renew_license(data)` | Renew a license | `key`, `next_renew_date` or `additional_days` |
| `add_credits(data)` | Add credits to a license | `key` or device info, `amount`, `description` |
| `list_licenses()` | Get all licenses | None |

### Client Token Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `verify_license(data)` | Verify license and device | `key` or device info (`domain`, `hostname`, `machine_id`, etc.) |
| `get_license_info(data)` | Get license information | `key` or device info |
| `activate_license(data)` | Activate license on device | `key` or device info, `version` |
| `deactivate_license(data)` | Deactivate license | `key` or device info |
| `send_heartbeat(data)` | Send heartbeat | `key` or device info, `version` |
| `get_credits_balance(data)` | Get credit balance | `key` or device info |
| `get_credits_info(data)` | Get credit information | `key` or device info |
| `reduce_credits(data)` | Reduce credits | `key` or device info, `amount`, `description` |
| `get_product_updates(...)` | Get product updates | `product`, `product_id`, or `key` (all optional with product token) |
| `get_product_changelog(...)` | Get product changelog | `product`, `product_id`, or `key` (all optional with product token) |
| `download_product(data)` | Download product version | `key` or device info, `version` |
| `get_secret_files(data)` | Get secret files | `key` or device info, `version` (optional) |
| `get_notifications(...)` | Get notifications | `product_id` (optional) |
| `verify_envato_purchase(data)` | Verify Envato purchase | `code`, `product_id`, `email`, `auto_issue` |

---

## License

MIT
