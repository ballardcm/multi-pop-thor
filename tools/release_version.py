"""Date-based public versions with a monotonically ordered updater value."""

from datetime import date
import json


def read_release(root):
    path = root / 'release-version.json'
    if not path.exists():
        return None
    config = json.loads(path.read_text())
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported release-version schema')
    day = date.fromisoformat(config['date'])
    revision = config['revision']
    if day.isoformat() != config['date'] or not 2000 <= day.year <= 2099:
        raise ValueError('Use an ISO release date between 2000 and 2099')
    if type(revision) is not int or not 1 <= revision <= 999:
        raise ValueError('Daily release revision must be an integer from 1 to 999')
    label = day.strftime('%m.%d.%y') + '.' + str(revision)
    # Preserve the integer field understood by every previously shipped updater.
    # Reserving three digits for the revision keeps the next day strictly newer.
    sequence = int(day.strftime('%Y%m%d')) * 1000 + revision
    return sequence, label
