"""Safely inspect Brazuca's channel favorites without modifying them."""
import json
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024


def has_channel_favorites(filename):
    """Avoid opening the native favorites menu when it would notify on empty.

    Legacy lists, missing and malformed files are left untouched. The native
    add-on is still responsible for resolving and displaying valid favorites.
    """
    try:
        path = Path(filename)
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return False
        with path.open('r', encoding='utf-8') as stream:
            data = json.load(stream)
        return isinstance(data, dict) and isinstance(data.get('canais'), list) and bool(data['canais'])
    except (OSError, ValueError, TypeError):
        return False
