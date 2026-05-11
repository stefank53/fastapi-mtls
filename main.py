"""Minimal FastAPI server that responds to /ping with a pong message over mTLS.

The server listens on port 8443 and requires mutual TLS authentication:
the server presents its own certificate (signed by a CA the client trusts),
and the client must present a certificate signed by the CA configured here.
"""

import ssl

import uvicorn
from fastapi import FastAPI

# FastAPI application instance. Defined at module scope (rather than inside
# ``if __name__ == "__main__"``) so external ASGI servers — for example,
# running ``uvicorn main:app`` from the command line — can also import it.
app = FastAPI()


@app.get("/ping")
async def ping() -> dict[str, str]:
    """Return a simple pong response.

    Used as a lightweight health check. FastAPI automatically serializes the
    returned dict to JSON and sets the Content-Type header to application/json.
    """
    return {"message": "pong"}


if __name__ == "__main__":
    # Start the uvicorn server with TLS enabled. This block only runs when the
    # file is executed directly (``python main.py``); it is skipped on import.
    uvicorn.run(
        app,
        # Bind to all interfaces so the server is reachable from outside the
        # host as well as via localhost. Use "127.0.0.1" instead to restrict
        # access to the local machine only.
        host="0.0.0.0",
        # Port 8443 is the conventional alternative HTTPS port (8000 + 443).
        port=8443,
        # Private key matching the server certificate below. Keep this file
        # readable only by the user running the server.
        ssl_keyfile="server.key",
        # Server certificate presented to clients during the TLS handshake.
        # Should contain the full chain (leaf + any intermediates) if signed
        # by a CA that uses intermediates.
        ssl_certfile="server.pem",
        # CA bundle used to verify CLIENT certificates. This is independent
        # of the trust store the client uses to verify the server. Only certs
        # chaining to a CA in this file will be accepted for mTLS.
        ssl_ca_certs="ca.pem",
        # Require every client to present a valid certificate. Without this,
        # clients could connect without authenticating, which would defeat
        # the purpose of mTLS. CERT_REQUIRED both requests a cert and fails
        # the handshake if one is not provided or fails verification.
        ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
