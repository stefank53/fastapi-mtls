"""Diagnostic script that exercises the mTLS handshake at the raw ssl layer.

This script bypasses higher-level HTTP libraries (httpx, requests) so any
TLS failure is reported directly by Python's stdlib ssl module rather than
being wrapped in a generic "connection failed" exception. Useful for
isolating whether a problem lives in the TLS configuration itself or in
the HTTP client.

On success it prints:
  - the number and subject(s) of trusted CAs loaded into the context
  - the negotiated cipher and TLS version
  - the subject of the server's certificate
"""

import socket
import ssl


def main() -> None:
    """Build an mTLS context, connect to the local server, and print details."""
    # Create an SSL context with secure defaults: TLS 1.2+, hostname
    # verification enabled, and certificate verification required. The
    # ``cafile`` argument supplies the trust anchor used to validate the
    # server's certificate during the handshake.
    ctx = ssl.create_default_context(cafile="ca.pem")

    # Load this client's certificate and private key. These are presented
    # to the server when it requests a client certificate (which it does
    # because it was started with ssl_cert_reqs=CERT_REQUIRED).
    ctx.load_cert_chain(certfile="client.pem", keyfile="client.key")

    # Report which CA(s) the context will trust when verifying the server.
    # If this prints 0, the ca.pem file is missing, empty, or not in PEM
    # format — a common silent failure mode.
    print("Trusted CAs loaded:", len(ctx.get_ca_certs()))
    for ca in ctx.get_ca_certs():
        print("  Subject:", ca.get("subject"))

    # Open a plain TCP connection first, then wrap it in TLS. ``wrap_socket``
    # performs the handshake immediately, so any cert/key/CA problem raises
    # an ssl.SSLError here rather than later during I/O. The
    # ``server_hostname`` argument enables SNI and is also used to verify
    # that the server cert's SAN matches the hostname we asked for.
    with socket.create_connection(("localhost", 8443)) as sock:
        with ctx.wrap_socket(sock, server_hostname="localhost") as ssock:
            # ``cipher()`` returns a tuple of (suite name, TLS version,
            # secret bits) — useful for confirming the negotiated protocol.
            print("Connected. Cipher:", ssock.cipher())

            # ``getpeercert()`` returns the parsed server certificate.
            # Printing the subject confirms which cert the server actually
            # presented, which is handy when troubleshooting multi-cert
            # setups (e.g. SNI misconfiguration).
            print("Peer cert subject:", ssock.getpeercert().get("subject"))


if __name__ == "__main__":
    main()
