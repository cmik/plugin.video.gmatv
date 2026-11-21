# -*- coding: utf-8 -*-
"""Catalog seed: build (.github/scripts/build_seed.py), download checks, install and rollback"""

import importlib.util
import json
import os
import pathlib
import sqlite3
import tempfile
import unittest
from unittest import mock

import test_userdata  # noqa: F401 (replaces the Kodi modules)
from resources.lib.libraries import seed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('build_seed', os.path.join(ROOT, '.github', 'scripts', 'build_seed.py'))
build_seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_seed)


def makeDb(path, table, rows, extra=''):
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE %s (ID INTEGER PRIMARY KEY, NAME TEXT%s)' % (table, extra))
    for i in range(rows):
        if extra:
            db.execute('INSERT INTO %s VALUES (?, ?, 5, 4, 3)' % table, (i, 'name %d' % i))
        else:
            db.execute('INSERT INTO %s VALUES (?, ?)' % table, (i, 'name %d' % i))
    db.commit()
    db.close()


class SeedTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.profile = os.path.join(self.dir, 'profile')
        self.published = os.path.join(self.dir, 'published')
        self.target = os.path.join(self.dir, 'target')
        for d in (self.profile, self.target):
            os.makedirs(d)
        counters = ', VIEWS INTEGER, RATING INTEGER, VOTES INTEGER'
        makeDb(os.path.join(self.profile, 'shows.db'), 'SHOW', 350, counters)
        makeDb(os.path.join(self.profile, 'episodes.db'), 'EPISODE', 20, counters)
        makeDb(os.path.join(self.profile, 'celebrities.db'), 'SHOW_CAST', 5)
        self.manifest = build_seed.build(self.profile, self.published, '2026-11-21', ROOT)
        self.url = pathlib.Path(self.published).as_uri() + '/'
        self.targets = dict((name, os.path.join(self.target, name)) for name, _, _ in seed.DATABASES)

    def count(self, name, table):
        db = sqlite3.connect(self.targets[name])
        try:
            return db.execute('SELECT COUNT(*) FROM %s' % table).fetchone()[0]
        finally:
            db.close()

    def test_seed_reason(self):
        self.assertEqual('install', seed.seedReason(''))
        self.assertEqual('major', seed.seedReason('1.0.2'))
        self.assertEqual('major', seed.seedReason('x'))
        self.assertIsNone(seed.seedReason('2.0.0~dev4'))
        self.assertIsNone(seed.seedReason('2.1.0'))

    def test_build_resets_the_counters(self):
        self.assertEqual({'shows': 350, 'episodes': 20, 'celebrities': 5}, self.manifest['counts'])
        db = sqlite3.connect(os.path.join(self.profile, 'shows.db'))
        self.assertEqual((5, 4, 3), db.execute('SELECT VIEWS, RATING, VOTES FROM SHOW WHERE ID = 1').fetchone())  # source untouched
        db.close()
        self.assertTrue(seed.installCatalogSeed(self.url, self.targets))
        db = sqlite3.connect(self.targets['shows.db'])
        self.assertEqual((0, 0, 0), db.execute('SELECT MAX(VIEWS), MAX(RATING), MAX(VOTES) FROM SHOW').fetchone())
        db.close()

    def test_install_replaces_and_keeps_a_backup(self):
        makeDb(self.targets['shows.db'], 'SHOW', 2)
        progress = []
        manifest = seed.installCatalogSeed(self.url, self.targets, progress.append)
        self.assertEqual('2026-11-21', manifest['catalogVersion'])
        self.assertEqual(350, self.count('shows.db', 'SHOW'))
        self.assertEqual(5, self.count('celebrities.db', 'SHOW_CAST'))
        self.assertTrue(os.path.exists(self.targets['shows.db'] + '.bak'))
        self.assertEqual(100, progress[-1])
        # the temporary folder is removed
        self.assertEqual([], [n for n in os.listdir(self.target) if n.startswith('gmatv-seed-')])

    def test_corrupted_download_leaves_the_databases(self):
        makeDb(self.targets['shows.db'], 'SHOW', 2)
        with open(os.path.join(self.published, 'manifest.json'), 'w') as f:
            json.dump(dict(self.manifest, sha256='0' * 64), f)
        self.assertIsNone(seed.installCatalogSeed(self.url, self.targets))
        self.assertEqual(2, self.count('shows.db', 'SHOW'))

    def test_too_few_rows_is_refused(self):
        with open(os.path.join(self.published, 'manifest.json'), 'w') as f:
            json.dump(dict(self.manifest, counts={'shows': 1000}), f)
        self.assertIsNone(seed.installCatalogSeed(self.url, self.targets))
        self.assertFalse(os.path.exists(self.targets['shows.db']))

    def test_no_or_bad_manifest(self):
        self.assertIsNone(seed.installCatalogSeed(pathlib.Path(self.dir).as_uri() + '/none/', self.targets))
        with open(os.path.join(self.published, 'manifest.json'), 'w') as f:
            json.dump({'format': 99}, f)
        self.assertIsNone(seed.installCatalogSeed(self.url, self.targets))

    def test_failed_install_is_rolled_back(self):
        makeDb(self.targets['shows.db'], 'SHOW', 2)
        makeDb(self.targets['episodes.db'], 'EPISODE', 3)
        real = os.replace
        calls = []

        def failSecond(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError('disk full')
            return real(src, dst)

        with mock.patch('os.replace', failSecond):
            self.assertIsNone(seed.installCatalogSeed(self.url, self.targets))
        self.assertEqual(2, self.count('shows.db', 'SHOW'))
        self.assertEqual(3, self.count('episodes.db', 'EPISODE'))


if __name__ == '__main__':
    unittest.main()
