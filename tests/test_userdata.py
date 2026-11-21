# -*- coding: utf-8 -*-
"""Tests of the models outside Kodi: python -m unittest discover -s tests"""

import os
import sqlite3
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class _Logger(object):
    def __getattr__(self, name):
        return lambda message, *a, **k: message


# the models import resources.lib.libraries.control, which needs Kodi: replace it
control = types.ModuleType('resources.lib.libraries.control')
control.logger = _Logger()
libraries = types.ModuleType('resources.lib.libraries')
libraries.control = control
libraries.__path__ = [os.path.join(ROOT, 'resources', 'lib', 'libraries')]  # the other modules are the real ones
sys.modules['resources.lib.libraries'] = libraries
sys.modules['resources.lib.libraries.control'] = control

from resources.lib.models import episodes, shows, userdata  # noqa: E402


def show(i, views=0):
    return {'id': i, 'name': 'Show %d' % i, 'parentid': -1, 'parentname': 'Cat', 'logo': 'l', 'image': 'i', 'fanart': 'f',
            'banner': 'b', 'url': 'u', 'description': 'd', 'shortdescription': 'd', 'year': '2020', 'ltype': 'show',
            'duration': 0, 'views': views, 'rating': 0, 'votes': 0}


def episode(i, showId=1, views=0):
    return {'id': i, 'title': 'Episode %d' % i, 'parentid': showId, 'show': 'S', 'image': 'i', 'fanart': 'f',
            'episodenumber': i, 'url': 'u', 'description': 'd', 'shortdescription': 'd', 'date': '2020-01-02',
            'year': '2020', 'parentalAdvisory': 'G', 'ltype': 'episode', 'duration': 10, 'views': views, 'rating': 0, 'votes': 0}


class UserDataTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ud = userdata.UserData(os.path.join(self.dir, 'userdata.db'))
        self.shows = shows.Show(os.path.join(self.dir, 'shows.db'))
        self.episodes = episodes.Episode(os.path.join(self.dir, 'episodes.db'))
        self.shows._userdata = self.episodes._userdata = self.ud

    def test_meta(self):
        self.assertIsNone(self.ud.getMeta('a'))
        self.ud.setMeta('a', 1)
        self.ud.setMeta('a', 2)
        self.assertEqual('2', self.ud.getMeta('a'))
        for key in ('x:a', 'x:b', 'xy', 'other'):
            self.ud.setMeta(key, '1')
        self.ud.deleteMeta('x:')
        self.assertEqual([None, None], [self.ud.getMeta('x:a'), self.ud.getMeta('x:b')])
        self.assertEqual(['1', '1'], [self.ud.getMeta('xy'), self.ud.getMeta('other')])

    def test_views_are_read_from_the_user_data(self):
        self.shows.set([show(1), show(2)])
        self.assertTrue(self.shows.update({'id': 1, 'views': 3, 'rating': 4}))
        self.assertEqual([(3, 4, 0)], [(s['views'], s['rating'], s['votes']) for s in self.shows.get(1)])
        self.assertEqual(0, self.shows.get(2)[0]['views'])
        self.assertEqual({1: 3}, dict((s['id'], s['views']) for s in self.shows.search({'TITLE': 'Show 1'})))
        # nothing is written in the catalog database
        raw = sqlite3.connect(os.path.join(self.dir, 'shows.db')).execute('SELECT VIEWS, RATING FROM SHOW WHERE ID = 1').fetchone()
        self.assertEqual((0, 0), raw)

    def test_replacing_the_catalog_keeps_the_views(self):
        self.shows.set([show(1)])
        self.episodes.set([episode(10)])
        self.shows.update({'id': 1, 'views': 5})
        self.episodes.update({'id': 10, 'views': 2})
        # a catalog refresh writes the items again, with views at 0
        self.shows.set([show(1, views=0)])
        self.episodes.set([episode(10, views=0)])
        self.assertEqual(5, self.shows.get(1)[0]['views'])
        self.assertEqual(2, self.episodes.get(10)[0]['views'])
        # and so does dropping the tables
        self.shows.drop()
        self.episodes.drop()
        self.shows.set([show(1)])
        self.assertEqual(5, self.shows.get(1)[0]['views'])
        self.assertEqual(2, self.ud.getViews(userdata.EPISODE, 10))

    def test_update_of_the_other_fields_keeps_the_views(self):
        self.episodes.set([episode(10)])
        self.episodes.update({'id': 10, 'views': 1})
        self.episodes.update({'id': 10, 'image': 'new'})
        e = self.episodes.get(10)[0]
        self.assertEqual((1, 'new'), (e['views'], e['image']))

    def test_history(self):
        self.ud.addToHistory(10, 1, 'Ep 10', 'Show 1', 't', 'episode', viewed='2026-01-01 10:00:00')
        self.ud.addToHistory(11, 1, 'Ep 11', 'Show 1', 't', 'episode', viewed='2026-01-02 10:00:00')
        self.ud.addToHistory(10, 1, 'Ep 10', 'Show 1', 't', 'episode', viewed='2026-01-03 10:00:00')
        history = self.ud.getHistory()
        self.assertEqual(['10', '11'], [h['episodeid'] for h in history])  # last viewed first, one line per episode
        self.assertEqual(2, self.ud.countHistory())
        self.ud.setStats(userdata.EPISODE, 10, views=2)
        self.ud.removeFromHistory(10)
        self.assertEqual(['11'], [h['episodeid'] for h in self.ud.getHistory()])
        self.assertEqual(0, self.ud.getViews(userdata.EPISODE, 10))
        self.ud.clearHistory()
        self.assertEqual([], self.ud.getHistory())

    def test_my_list(self):
        self.assertEqual([], self.ud.getMyList())
        self.ud.addToMyList(1000002521, 'A movie')
        self.ud.addToMyList(17, 'A show')
        self.ud.addToMyList(17, 'A show')  # added twice: listed once
        self.assertEqual(['17', '1000002521'], self.ud.getMyListIds())  # the last added first
        self.assertTrue(self.ud.removeFromMyList(1000002521))
        self.assertFalse(self.ud.removeFromMyList(1000002521))
        self.assertEqual([('17', 'A show')], self.ud.getMyList())

    def test_history_limit(self):
        self.ud.historyLimit = 5
        for i in range(12):
            self.ud.addToHistory(i, 1, 'Ep', 'S', 't', 'episode')
        self.assertEqual(5, len(self.ud.getHistory(limit=100)))

    def test_import_legacy(self):
        # the previous versions stored the counters in the catalog columns
        shows.Show(os.path.join(self.dir, 'old_shows.db')).set([show(1)])
        episodes.Episode(os.path.join(self.dir, 'old_episodes.db')).set([episode(10)])
        con = sqlite3.connect(os.path.join(self.dir, 'old_shows.db'))
        con.execute('UPDATE SHOW SET VIEWS = 7, RATING = 3 WHERE ID = 1')
        con.commit()
        con.close()
        con = sqlite3.connect(os.path.join(self.dir, 'old_episodes.db'))
        con.execute('UPDATE EPISODE SET VIEWS = 2 WHERE ID = 10')
        con.commit()
        con.close()
        old = (os.path.join(self.dir, 'old_shows.db'), os.path.join(self.dir, 'old_episodes.db'))
        self.assertEqual(2, self.ud.importLegacy(*old))
        self.assertEqual((7, 3, 0), self.ud.getStats(userdata.SHOW, [1])['1'])
        self.assertEqual(2, self.ud.getViews(userdata.EPISODE, 10))
        # done once: what was changed since is not overwritten by a second import
        self.ud.setStats(userdata.SHOW, 1, views=9)
        self.assertEqual(0, self.ud.importLegacy(*old))
        self.assertEqual(9, self.ud.getViews(userdata.SHOW, 1))

    def test_import_legacy_without_files(self):
        self.assertEqual(0, self.ud.importLegacy(os.path.join(self.dir, 'nope.db'), os.path.join(self.dir, 'nope2.db')))


if __name__ == '__main__':
    unittest.main()
