#!/usr/bin/env python3
"""Build the catalog seed from the databases of a Kodi profile.

    python3 .github/scripts/build_seed.py <addon_data folder> <output folder> [--catalog-version 2026-11-21]

The addon_data folder is the one of the add-on in the Kodi profile (it holds shows.db,
episodes.db and celebrities.db, filled by Tools > Reset Catalog Cache or Update Catalog).
The output folder gets catalog-seed.zip and manifest.json: publish them as the assets of the
GitHub release `catalog-seed`:

    gh release create catalog-seed <output>/catalog-seed.zip <output>/manifest.json --title "Catalog seed" --notes "..."   # first time
    gh release upload catalog-seed <output>/catalog-seed.zip <output>/manifest.json --clobber                              # next ones

The user data lives in userdata.db, which is not part of the seed; the counter columns that the
catalog tables still have (VIEWS, RATING, VOTES) are set to 0 in the copies. The source databases
are not modified.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile

FORMAT = 1
ZIP_NAME = 'catalog-seed.zip'
# file -> (table, manifest count key, minimum rows of a usable database, columns to reset)
DATABASES = {
    'shows.db': ('SHOW', 'shows', 300, 'VIEWS = 0, RATING = 0, VOTES = 0'),
    'episodes.db': ('EPISODE', 'episodes', 1, 'VIEWS = 0, RATING = 0, VOTES = 0'),
    'celebrities.db': ('SHOW_CAST', 'celebrities', 1, None),
}


def addonVersion(root):
    with open(os.path.join(root, 'addon.xml'), encoding='utf-8') as f:
        return re.search(r'<addon[^>]*\sversion="([^"]+)"', f.read()).group(1)


def sanitize(source, target, table, reset):
    shutil.copyfile(source, target)
    db = sqlite3.connect(target)
    try:
        if reset:
            db.execute('UPDATE %s SET %s' % (table, reset))
            db.commit()
        db.execute('VACUUM')
        return db.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
    finally:
        db.close()


def build(source, output, catalogVersion, root):
    os.makedirs(output, exist_ok=True)
    counts = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (table, key, minimum, reset) in DATABASES.items():
            path = os.path.join(source, name)
            if not os.path.exists(path):
                raise SystemExit('%s not found in %s' % (name, source))
            counts[key] = sanitize(path, os.path.join(tmp, name), table, reset)
            if counts[key] < minimum:
                raise SystemExit('%s has only %d rows (at least %d expected): load the catalog first' % (name, counts[key], minimum))
        zipPath = os.path.join(output, ZIP_NAME)
        with zipfile.ZipFile(zipPath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in DATABASES:
                archive.write(os.path.join(tmp, name), name)

    with open(zipPath, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    manifest = {
        'format': FORMAT,
        'catalogVersion': catalogVersion,
        'addonVersion': addonVersion(root),
        'file': ZIP_NAME,
        'size': os.path.getsize(zipPath),
        'sha256': sha256,
        'counts': counts,
    }
    with open(os.path.join(output, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--catalog-version', default=datetime.date.today().isoformat())
    args = parser.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(json.dumps(build(args.source, args.output, args.catalog_version, root), indent=2))


if __name__ == '__main__':
    sys.exit(main())
