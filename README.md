# FastAPI mTLS Server — Setup and Test Notes

End-to-end commands for setting up a Python virtual environment, generating
the certificate chain, running the FastAPI mTLS server, and testing it from
a client.

---

## 1. Environment Setup

### Create the virtual environment

Creates an isolated Python environment in `.venv/` so project dependencies
don't affect the system Python.

```bash
python3 -m venv .venv
```

### Activate the virtual environment

Switches the current shell to use the venv's Python and pip. The shell
prompt will show `(.venv)` while it's active.

```bash
source .venv/bin/activate
```

### Install Python packages

Installs the FastAPI framework, the uvicorn ASGI server that runs it, and
the httpx HTTP client used by `client.py`.

```bash
pip install fastapi uvicorn httpx
```

---

## 2. Certificate Creation

All commands below assume the OpenSSL config files (`ca.cfg`, `server.cfg`,
`client.cfg`) are in the current directory and contain the relevant
`extendedKeyUsage` and `subjectAltName` extensions.

### Generate a self-signed Root CA

Creates a new RSA private key (`ca.key`) and a self-signed root certificate
(`ca.pem`). This CA will sign both the server and client certificates.

```bash
openssl req -x509 -new -nodes -keyout ca.key -out ca.pem -config ca.cfg
```

### Create a CSR for the server

Generates the server's private key (`server.key`) and a Certificate Signing
Request (`server.csr`). The CSR carries the subject and extension requests
defined in `server.cfg`.

```bash
openssl req -new -newkey rsa:2048 -nodes \
    -keyout server.key -out server.csr -config server.cfg
```

### Sign the server certificate with the CA

The CA signs the CSR to produce `server.pem`. The `-extfile` and
`-extensions` flags carry the `serverAuth` EKU and SAN entries from the
config file into the final certificate — without these, the extensions
would be dropped.

```bash
openssl x509 -req -in server.csr \
    -CA ca.pem -CAkey ca.key -CAcreateserial \
    -out server.pem \
    -extfile server.cfg -extensions v3_req
```

### Verify the server cert has the serverAuth EKU

Confirms the Extended Key Usage extension was applied correctly. Expected
output: `TLS Web Server Authentication`.

```bash
openssl x509 -in server.pem -noout -ext extendedKeyUsage
```

### Create a CSR for the client

Same pattern as the server CSR, but using `client.cfg` (which requests the
`clientAuth` EKU instead).

```bash
openssl req -new -newkey rsa:2048 -nodes \
    -keyout client.key -out client.csr -config client.cfg
```

### Sign the client certificate with the CA

Produces `client.pem`, signed by the same CA as the server cert.

```bash
openssl x509 -req -in client.csr \
    -CA ca.pem -CAkey ca.key -CAcreateserial \
    -out client.pem \
    -extfile client.cfg -extensions v3_req
```

### Verify the client cert has the clientAuth EKU

Expected output: `TLS Web Client Authentication`.

```bash
openssl x509 -in client.pem -noout -ext extendedKeyUsage
```

---

## 3. Running the Test

### Terminal 1 — start the server

Run the server directly via the `__main__` block in `main.py`:

```bash
python main.py
```

Or invoke uvicorn from the command line with explicit TLS flags. The
`--ssl-cert-reqs 2` value corresponds to `ssl.CERT_REQUIRED` and enforces
mTLS:

```bash
uvicorn main:app \
    --host 0.0.0.0 --port 8443 \
    --ssl-keyfile server.key \
    --ssl-certfile server.pem \
    --ssl-ca-certs ca.pem \
    --ssl-cert-reqs 2
```

### Terminal 2 — test from the client

Activate the venv in the new terminal (each shell needs its own activation):

```bash
source .venv/bin/activate
```

Run the Python client:

```bash
python client.py
```

Or test with curl, which is useful for ruling out Python-specific issues:

```bash
curl --cacert ca.pem \
     --cert client.pem --key client.key \
     https://localhost:8443/ping
```

Expected response: `{"message":"pong"}`.

---

## 4. Troubleshooting

### Verify the certificate chain

Confirms each leaf certificate chains correctly back to the CA. Both should
print `OK`.

```bash
openssl verify -CAfile ca.pem server.pem
openssl verify -CAfile ca.pem client.pem
```

### Inspect a certificate's full contents

Useful when something is rejected and the cause isn't obvious. Shows the
subject, issuer, validity period, SAN, EKU, and other extensions.

```bash
openssl x509 -in server.pem -noout -text
```

### Test the TLS handshake directly

Bypasses the HTTP layer entirely. The output will show the negotiated
cipher, certificate chain, and any verification errors.

```bash
openssl s_client -connect localhost:8443 \
    -CAfile ca.pem \
    -cert client.pem -key client.key \
    </dev/null
```

### See what's listening on port 8443

Useful if you get an "address already in use" error when starting the
server.

```bash
sudo lsof -i :8443
```

---

## 5. Environment Cleanup

### Remove certificate files for a fresh start

Deletes all keys, certs, CSRs, and the CA serial file. Run this when you
want to regenerate the entire chain from scratch.

```bash
rm -f *.key *.pem *.csr *.srl
```

### Create .crt copies for GUI inspection

Some certificate viewers (Windows Explorer, Keychain Access) only
recognize the `.crt` extension even though the file format is identical
to `.pem`.

```bash
cp server.pem server.crt
cp client.pem client.crt
```

### Deactivate the virtual environment

Returns the shell to the system Python. The `.venv/` directory remains
intact and can be reactivated later.

```bash
deactivate
```