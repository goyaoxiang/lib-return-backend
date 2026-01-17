# Self-Signed HTTPS Certificate Setup (IP Address)

This guide explains how to set up HTTPS for your backend using self-signed certificates with an IP address (no domain required).

---

## Prerequisites

- Existing CA certificate and key in `~/certs/` directory
- OpenSSL installed
- Backend service configured

---

## Step 1: Get Your Server IP Address

Find your GCP Compute Engine instance's external IP:

```bash
# On your VM
curl -s ifconfig.me
# Or check in GCP Console: Compute Engine > VM instances > External IP
```

**Note the IP address** - you'll need it for certificate generation.

---

## Step 2: Generate HTTPS Certificate

### Option A: Using the Script (Recommended)

```bash
cd ~/library-return/backend
chmod +x generate-https-cert.sh
./generate-https-cert.sh YOUR_IP_ADDRESS 443
```

**Replace** `YOUR_IP_ADDRESS` with your actual IP (e.g., `34.142.123.45`).

The script will:

- Generate a server certificate signed by your existing CA
- Create certificate files in `backend/ssl-certs/`
- Set proper permissions

### Option B: Manual Generation

If you prefer to generate manually:

```bash
cd ~/library-return/backend
mkdir -p ssl-certs
cd ssl-certs

# Generate server private key
openssl genrsa -out backend-server-key.pem 2048

# Create certificate signing request with IP in SAN
openssl req -new -key backend-server-key.pem -out backend-server.csr \
    -subj "/C=MY/ST=Penang/L=Georgetown/O=Library/CN=backend-server" \
    -addext "subjectAltName=IP:34.57.9.40"

# Sign certificate with your CA
openssl x509 -req -days 365 -in backend-server.csr \
    -CA ~/certs/ca-cert.pem -CAkey ~/certs/ca-key.pem -CAcreateserial \
    -out backend-server-cert.pem \
    -extensions v3_req -extfile <(
        echo "[v3_req]"
        echo "subjectAltName=IP:34.57.9.40"
    )

# Clean up
rm backend-server.csr

# Set permissions
chmod 600 backend-server-key.pem
chmod 644 backend-server-cert.pem
```

**Replace** `YOUR_IP_ADDRESS` with your actual IP address.

---

## Step 3: Update Backend Configuration

### Update `.env` File

Edit `~/library-return/backend/.env`:

```env
# Server Configuration
HOST=0.0.0.0
PORT=443

# HTTPS/SSL Configuration
SSL_ENABLED=true
SSL_CERTFILE=./ssl-certs/backend-server-cert.pem
SSL_KEYFILE=./ssl-certs/backend-server-key.pem

# ... rest of your configuration
```

### Update Systemd Service

Edit `/etc/systemd/system/library-backend.service`:

```ini
[Unit]
Description=Library Return System Backend
After=network.target postgresql.service mosquitto.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/library-return/backend
Environment="PATH=/home/your_username/library-return/backend/venv/bin"
EnvironmentFile=/home/your_username/library-return/backend/.env
ExecStart=/bin/bash -c 'if [ "$SSL_ENABLED" = "true" ]; then /home/your_username/library-return/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --ssl-certfile "${SSL_CERTFILE}" --ssl-keyfile "${SSL_KEYFILE}"; else /home/your_username/library-return/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT}; fi'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Replace** `your_username` with your actual username.

---

## Step 4: Configure Firewall

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Block HTTP port 3000 from external (optional)
sudo ufw deny 3000/tcp
```

---

## Step 5: Restart Backend Service

```bash
sudo systemctl daemon-reload
sudo systemctl restart library-backend
sudo systemctl status library-backend
```

---

## Step 6: Test HTTPS Connection

```bash
# Test from server
curl -k https://YOUR_IP_ADDRESS/api/health

# Test with certificate verification (will fail with self-signed, but shows connection works)
curl --cacert ~/certs/ca-cert.pem https://YOUR_IP_ADDRESS/api/health
```

---

## Step 7: Mobile App Configuration

### Update Flutter App `.env`

Edit `lib_return/.env`:

```env
BASE_URL=https://YOUR_IP_ADDRESS
API_PORT=443
```

**Replace** `YOUR_IP_ADDRESS` with your actual IP address.

### Copy CA Certificate to Mobile App

The mobile app needs to trust your CA certificate:

```bash
# Copy CA certificate to mobile app assets
mkdir -p ~/library-return/lib_return/assets
cp ~/certs/ca-cert.pem ~/library-return/lib_return/assets/ca-cert.pem
```

### Update Flutter App to Trust CA Certificate

#### Option A: Certificate Pinning (Recommended)

Create `lib_return/lib/services/ssl_certificate_pinning.dart`:

```dart
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

class SSLCertificatePinning {
  static Future<http.Client> createClient() async {
    final caCert = await rootBundle.load('assets/ca-cert.pem');
    final securityContext = SecurityContext.defaultContext;
    securityContext.setTrustedCertificatesBytes(caCert.buffer.asUint8List());

    final httpClient = HttpClient(context: securityContext);
    return IOClient(httpClient);
  }
}
```

Update `lib_return/lib/services/api_service.dart`:

```dart
import 'ssl_certificate_pinning.dart';

class ApiService {
  final http.Client _client;

  ApiService() : _client = http.Client();

  // For HTTPS with self-signed cert, use:
  // ApiService() : _client = await SSLCertificatePinning.createClient();

  // ... rest of your code
}
```

#### Option B: Android Network Security Config

Create `lib_return/android/app/src/main/res/xml/network_security_config.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">YOUR_IP_ADDRESS</domain>
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </domain-config>
</network-security-config>
```

Update `lib_return/android/app/src/main/AndroidManifest.xml`:

```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

#### Option C: iOS App Transport Security

Update `lib_return/ios/Runner/Info.plist`:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <false/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>YOUR_IP_ADDRESS</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <false/>
            <key>NSIncludesSubdomains</key>
            <true/>
            <key>NSExceptionRequiresForwardSecrecy</key>
            <false/>
            <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
            <false/>
        </dict>
    </dict>
</dict>
```

**Note**: Replace `YOUR_IP_ADDRESS` with your actual IP address in all configurations.

---

## Troubleshooting

### Certificate Verification Failed

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution**:

- Ensure CA certificate is copied to mobile app assets
- Verify certificate pinning is configured correctly
- Check that IP address matches certificate SAN

### Connection Refused

**Error**: `Connection refused`

**Solution**:

- Verify backend is running: `sudo systemctl status library-backend`
- Check firewall allows port 443: `sudo ufw status`
- Verify IP address is correct

### Certificate Not Trusted (Mobile App)

**Error**: Certificate not trusted warnings

**Solution**:

- Use certificate pinning (Option A above)
- Or configure network security config (Android/iOS)
- Ensure CA certificate is properly included in app

---

## Security Notes

⚠️ **Important**: Self-signed certificates are for development/testing only. For production:

1. Use a proper domain name
2. Get certificates from Let's Encrypt (free)
3. Or use a trusted CA certificate

Self-signed certificates will:

- Show security warnings in browsers
- Require special configuration in mobile apps
- Not be trusted by default

---

## Complete Example

```bash
# 1. Generate certificate
cd ~/library-return/backend
./generate-https-cert.sh 34.142.123.45 443

# 2. Update backend .env
# SSL_ENABLED=true
# SSL_CERTFILE=./ssl-certs/backend-server-cert.pem
# SSL_KEYFILE=./ssl-certs/backend-server-key.pem
# PORT=443

# 3. Update systemd service (see Step 3)

# 4. Restart service
sudo systemctl restart library-backend

# 5. Update mobile app .env
# BASE_URL=https://34.142.123.45
# API_PORT=443

# 6. Copy CA cert to mobile app
cp ~/certs/ca-cert.pem ~/library-return/lib_return/assets/ca-cert.pem

# 7. Configure mobile app (see Step 7)
```

---

**Last Updated**: January 2025
