"""Environment-only Temporal connection settings; never log these options."""

import os


def connection_options() -> dict:
    key = os.getenv("TEMPORAL_API_KEY")
    tls = os.getenv("TEMPORAL_TLS", "true" if key else "false").lower() == "true"
    if key and not tls:
        raise ValueError("Temporal API keys require TLS")
    return {
        "namespace": os.getenv("TEMPORAL_NAMESPACE", "default"),
        "tls": tls,
        **({"api_key": key} if key else {}),
    }
