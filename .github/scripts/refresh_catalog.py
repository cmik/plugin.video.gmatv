#!/usr/bin/env python3
"""Refresh the catalog seed outside Kodi: download the published seed, load the shows that are new
since it was built (the code of Tools > Update Catalog (new shows), run with stand-ins for the Kodi
modules), then build a new seed.

    python3 .github/scripts/refresh_catalog.py <work folder> <output folder> [--seed-url URL] [--verbose]

The output folder gets catalog-seed.zip and manifest.json (see build_seed.py), and `changed` tells
whether there is anything new to publish: exit code 0 = new seed to publish, 3 = nothing new,
1 = error (nothing to publish). A new seed never has fewer rows than the published one.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import build_seed  # noqa: E402
import kodistub  # noqa: E402

NOTHING_NEW = 3


def download(url, path):
    request = urllib.request.Request(url, headers={'User-Agent': 'plugin.video.gmatv catalog refresh'})
    with urllib.request.urlopen(request, timeout=120) as response, open(path, 'wb') as f:
        f.write(response.read())


def fetchSeed(seedUrl, profile):
    """Install the published seed in the profile folder; returns its manifest"""
    os.makedirs(profile, exist_ok=True)
    manifestPath = os.path.join(profile, 'published-manifest.json')
    download(seedUrl + 'manifest.json', manifestPath)
    with open(manifestPath, encoding='utf-8') as f:
        manifest = json.load(f)
    zipPath = os.path.join(profile, manifest['file'])
    download(seedUrl + manifest['file'], zipPath)
    with open(zipPath, 'rb') as f:
        if hashlib.sha256(f.read()).hexdigest() != manifest['sha256']:
            raise SystemExit('The published seed does not match its manifest')
    with zipfile.ZipFile(zipPath) as archive:
        for name in build_seed.DATABASES:
            archive.extract(name, profile)
    os.remove(zipPath)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('work')
    parser.add_argument('output')
    parser.add_argument('--seed-url', default=None, help='where the published seed is (default: the catalogSeedURL setting)')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    profile = os.path.abspath(os.path.join(args.work, 'profile'))
    # no Kodi cache outside Kodi: the answers are only kept for the run
    settings = kodistub.install(ROOT, profile, {'cacheActive': 'false', 'debug': 'true' if args.verbose else 'false',
                                                'debugLevel': 'INFO'}, verbose=args.verbose)
    seedUrl = args.seed_url or settings.get('catalogSeedURL')
    published = fetchSeed(seedUrl, profile)
    print('Published seed %s: %s' % (published.get('catalogVersion'), published.get('counts')))

    # the add-on code reads the arguments Kodi gives a plugin (url, handle, query)
    sys.argv = ['plugin://plugin.video.gmatv/', '-1', '']
    # the errors of the add-on are always printed, the rest with --verbose
    from resources.lib.libraries import logger
    logger.enable(True)
    logger.setLevel(logger.LOGINFO if args.verbose else logger.LOGERROR)
    from resources.lib.sources import gmatv
    if gmatv.updateCatalogCache(False, True) is not True:
        print('The catalog could not be updated', file=sys.stderr)
        return 1

    manifest = build_seed.build(profile, args.output, datetime.date.today().isoformat(), ROOT)
    counts, before = manifest['counts'], published.get('counts', {})
    print('New seed %s: %s' % (manifest['catalogVersion'], counts))
    smaller = [k for k in counts if counts[k] < before.get(k, 0)]
    if smaller:
        print('The new seed has fewer rows than the published one (%s): not published' % ', '.join(smaller), file=sys.stderr)
        return 1
    changed = counts != before
    with open(os.path.join(args.output, 'changed'), 'w') as f:
        f.write('true\n' if changed else 'false\n')
    return 0 if changed else NOTHING_NEW


if __name__ == '__main__':
    sys.exit(main())
