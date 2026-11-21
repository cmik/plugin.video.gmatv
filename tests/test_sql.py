# -*- coding: utf-8 -*-
"""The values reach SQLite as parameters: quotes in titles, searches and ids don't break the queries"""

import os
import tempfile
import unittest

import test_userdata  # noqa: F401 (replaces the Kodi modules)
from test_userdata import show, episode
from resources.lib.models import episodes, shows, showcast, celebrities, library, userdata


class SqlParamsTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ud = userdata.UserData(os.path.join(self.dir, 'userdata.db'))
        self.shows = shows.Show(os.path.join(self.dir, 'shows.db'))
        self.episodes = episodes.Episode(os.path.join(self.dir, 'episodes.db'))
        self.shows._userdata = self.episodes._userdata = self.ud

    def test_show_with_quotes(self):
        s = show(1)
        s.update({'name': "It's Showtime", 'description': 'A "live" show', 'logo': 'http://x/it&#39;s.jpg'})
        self.assertTrue(self.shows.set([s, show(2)]))
        self.assertEqual(["It's Showtime"], [x['name'] for x in self.shows.searchByTitle("It's")])
        self.assertEqual("http://x/it's.jpg", self.shows.get(1)[0]['logo'])
        self.assertEqual([], self.shows.searchByTitle("x' OR '1'='1"))
        self.assertTrue(self.shows.update({'id': 1, 'name': "Lola's Show", 'year': '2021'}))
        got = self.shows.get(1)[0]
        self.assertEqual(("Lola's Show", '2021', 'A "live" show'), (got['name'], got['year'], got['description']))
        self.assertEqual(['Show 2'], [x['name'] for x in self.shows.get(['2'])])
        self.assertTrue(self.shows.delete([{'id': 1}]))
        self.assertEqual([2], [x['id'] for x in self.shows.getAll()])

    def test_episode_with_quotes(self):
        e = episode(10)
        e.update({'title': "Daig Kayo Ng Lola Ko: Lola's story", 'show': "Lola's"})
        self.assertTrue(self.episodes.set([e, episode(11)]))
        self.assertEqual([10], [x['id'] for x in self.episodes.searchByTitle("Lola's")])
        self.assertTrue(self.episodes.update({'id': 10, 'name': "Ep 'two'"}))
        self.assertEqual("Ep 'two'", self.episodes.get(10)[0]['title'])
        self.assertEqual([10, 11], sorted(x['id'] for x in self.episodes.getByShow(1)))

    def test_cast_and_actor_and_library(self):
        cast = showcast.ShowCast(os.path.join(self.dir, 'celebrities.db'))
        self.assertTrue(cast.set([{'showid': 1, 'castid': 2, 'name': "Ma'am Lyn", 'role': "D'Artagnan", 'thumbnail': 't', 'order': 1, 'url': ''}]))
        self.assertEqual(["D'Artagnan"], [c['role'] for c in cast.searchByActorName("Ma'am")])
        self.assertTrue(cast.update({'showid': 1, 'castid': 2, 'role': "O'Neil"}))
        self.assertEqual("O'Neil", cast.getByShow(1)[0]['role'])
        actors = celebrities.Actor(os.path.join(self.dir, 'celebrities.db'))
        self.assertTrue(actors.set([{'id': 5, 'name': "O'Hara", 'thumbnail': '', 'fanart': '', 'banner': '', 'url': '', 'description': "it's", 'birthday': '', 'birthplace': ''}]))
        self.assertEqual("O'Hara", actors.get(5)[0]['name'])
        lib = library.Library(os.path.join(self.dir, 'library.db'))
        self.assertTrue(lib.set([{'id': 3, 'name': "It's Showtime", 'parentid': -1, 'year': '2020', 'date': '2020-01-02'}]))
        self.assertEqual(["It's Showtime"], [x['name'] for x in lib.getAll()])

    def test_bad_column_or_sort_is_refused(self):
        self.shows.set([show(1)])
        self.assertEqual([], self.shows.search({'TITLE = 1 OR 1': 'x'}))
        self.assertEqual([], self.shows.search({'TITLE': 'Show'}, ['TITLE', 'ASC; DROP TABLE SHOW']))
        self.assertEqual(1, len(self.shows.getAll()))


if __name__ == '__main__':
    unittest.main()
