"""Small per-profile cache for real, successful widget results.

No backup/user files are modified outside this add-on's cache directory. Locks
coalesce the two movie widgets across Kodi's independent plugin invocations.
"""
import fcntl
import json
import os
import tempfile
from datetime import date

MAX_BYTES = 2 * 1024 * 1024


def cached(directory, name, fetch, successful, today=None):
    if name not in ('recent-movies', 'recent-series'):
        raise ValueError('Invalid widget cache name')
    today = (today or date.today()).isoformat()
    try:
        os.makedirs(directory, mode=0o700, exist_ok=True)
        lock = open(os.path.join(directory, name + '.lock'), 'a+b')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
    except OSError:
        return fetch()
    try:
        path = os.path.join(directory, name + '.json')
        try:
            if os.path.getsize(path) > MAX_BYTES:
                raise ValueError('Cache too large')
            with open(path, encoding='utf-8') as stream:
                data = json.load(stream)
            if (isinstance(data, dict) and data.get('version') == 1 and
                    data.get('date') == today and successful(data.get('value'))):
                return data['value']
        except (OSError, ValueError, TypeError):
            pass
        value = fetch()
        if successful(value):
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                                 prefix='.widget-', delete=False) as out:
                    tmp = out.name
                    json.dump({'version': 1, 'date': today, 'value': value}, out, ensure_ascii=False)
                if os.path.getsize(tmp) <= MAX_BYTES:
                    os.replace(tmp, path)
                    tmp = None
            except (OSError, TypeError, ValueError):
                pass  # A read-only/full profile must not break the widget.
            finally:
                if tmp is not None:
                    try: os.unlink(tmp)
                    except OSError: pass
        return value
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
