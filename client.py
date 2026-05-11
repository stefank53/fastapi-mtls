"""Simple mTLS client that sends a ping request to the local FastAPI server.

This client demonstrates mutual TLS authentication using httpx 0.28+.
It builds an ssl.SSLContext explicitly (rather than using httpx's removed
``cert=`` shortcut) so the same code works across recent httpx versions.
"""

import ssl

import httpx


def main() -> None:
    """Send a single GET /ping request over mTLS and print the response."""
    # Build an SSL context pre-loaded with the CA that signed the server's
    # certificate. ``create_default_context`` applies sensible defaults:
    # TLS 1.2+, hostname verification enabled, and certificate verification
    # required. ``cafile`` is the trust anchor used to validate the server.
    ctx = ssl.create_default_context(cafile="ca.pem")

    # Load this client's own certificate and private key. The server will
    # request a client certificate during the TLS handshake (because it was
    # started with ssl_cert_reqs=CERT_REQUIRED), and these files are what
    # we present to prove our identity.
    ctx.load_cert_chain(certfile="client.pem", keyfile="client.key")

    # Pass the pre-built context to httpx via ``verify=``. In httpx 0.28+ this
    # is the supported way to configure both server verification (the CA in
    # the context) and client authentication (the cert chain in the context).
    # Using a context manager ensures the underlying connection pool is
    # cleanly closed when we're done.
    with httpx.Client(verify=ctx) as client:
        # Issue the request. httpx performs the TLS handshake — including
        # presenting our client cert — before sending the HTTP request.
        response = client.get("https://localhost:8443/ping")

        # Raise an exception for any 4xx or 5xx response so failures surface
        # immediately rather than being silently ignored.
        response.raise_for_status()

        # Print the result. ``response.json()`` parses the JSON body returned
        # by the FastAPI handler (e.g. {"message": "pong"}).
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    main()
