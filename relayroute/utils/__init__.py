"""Shared utilities."""
import uuid


def generate_id(prefix: str) -> str:
    """Generate ID with prefix + short UUID (e.g. city_a3f9bc12)."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
