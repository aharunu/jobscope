"""SSRF protection and IP/DNS validation for outbound HTTP requests."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})
CARRIER_GRADE_NAT = ipaddress.ip_network("100.64.0.0/10")
BENCHMARK_NET = ipaddress.ip_network("198.18.0.0/15")


def is_ip_safe(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check whether an IP address is safe for outbound public requests."""
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False
    return not (
        isinstance(ip, ipaddress.IPv4Address)
        and (ip in CARRIER_GRADE_NAT or ip in BENCHMARK_NET)
    )


def validate_target_url_safety(url: str) -> tuple[bool, str | None, str | None]:
    """Validate that a URL uses http(s) and does not resolve to private/internal IPs.

    Returns:
        (is_safe, error_type, error_message)
        If safe: (True, None, None)
        If unsafe/invalid: (False, error_type, descriptive_message)
    """
    try:
        parsed = urlsplit(url)
    except Exception as exc:
        return False, "invalid_url", f"Failed to parse URL: {exc}"

    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return (
            False,
            "unsupported_scheme",
            (
                f"Unsupported URL scheme: '{parsed.scheme}'. "
                "Only http and https are permitted."
            ),
        )

    hostname = parsed.hostname
    if not hostname:
        return False, "invalid_url", "URL is missing a valid hostname."

    # Direct IP literal check
    try:
        direct_ip = ipaddress.ip_address(hostname)
        if not is_ip_safe(direct_ip):
            return (
                False,
                "ssrf_blocked",
                f"Target resolved to blocked or private IP: {direct_ip}",
            )
        return True, None, None
    except ValueError:
        pass

    # Resolve hostname via DNS
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    port = parsed.port or default_port

    try:
        addr_info = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        return (
            False,
            "dns_resolution_failed",
            f"DNS resolution failed for {hostname}: {exc}",
        )
    except Exception as exc:
        return (
            False,
            "dns_resolution_failed",
            f"Address lookup failed for {hostname}: {exc}",
        )

    if not addr_info:
        return (
            False,
            "dns_resolution_failed",
            f"No address records found for {hostname}.",
        )

    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if not is_ip_safe(ip):
                return (
                    False,
                    "ssrf_blocked",
                    f"Target resolved to blocked or private IP: {ip_str}",
                )
        except ValueError:
            return (
                False,
                "ssrf_blocked",
                f"Resolved address could not be parsed: {ip_str}",
            )

    return True, None, None
