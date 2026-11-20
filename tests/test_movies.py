# -*- coding: utf-8 -*-
"""Ids of the movies and search in the shows: python -m unittest discover -s tests"""

import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class _Logger(object):
    def __getattr__(self, name):
        return lambda message, *a, **k: message


control = types.ModuleType('resources.lib.libraries.control')
control.logger = _Logger()
libraries = types.ModuleType('resources.lib.libraries')
libraries.control = control
libraries.__path__ = [os.path.join(ROOT, 'resources', 'lib', 'libraries')]
sys.modules['resources.lib.libraries'] = libraries
sys.modules['resources.lib.libraries.control'] = control

from resources.lib.libraries import movies  # noqa: E402
from resources.lib.models import shows, userdata  # noqa: E402


def show(i, name, ltype='show'):
    return {'id': i, 'name': name, 'parentid': -1, 'parentname': 'Drama', 'logo': 'l', 'image': 'i', 'fanart': 'f',
            'banner': 'b', 'url': 'u', 'description': 'd', 'shortdescription': 'd', 'year': '2026', 'ltype': ltype,
            'duration': 0, 'views': 0, 'rating': 0, 'votes': 0}


class MoviesTest(unittest.TestCase):

    def test_ids(self):
        self.assertFalse(movies.isMovieId(2473))
        self.assertFalse(movies.isMovieId('331122'))
        self.assertFalse(movies.isMovieId(None))
        movieId = movies.toMovieId('2473')
        self.assertTrue(movies.isMovieId(movieId))
        self.assertNotEqual(2473, movieId)
        self.assertEqual(2473, movies.toApiId(movieId))
        self.assertEqual(2473, movies.toApiId(2473))
        self.assertEqual(2473, movies.toApiId(str(movieId)))

    def test_origin(self):
        self.assertTrue(movies.isMovie({'origin': 'fulleps'}))
        self.assertFalse(movies.isMovie({'origin': 'ent'}))
        self.assertFalse(movies.isMovie({}))

    def test_a_show_and_a_movie_with_the_same_website_id_can_be_stored(self):
        d = tempfile.mkdtemp()
        db = shows.Show(os.path.join(d, 'shows.db'))
        db._userdata = userdata.UserData(os.path.join(d, 'userdata.db'))
        db.set([show(2473, 'Delivery Boi'), show(movies.toMovieId(2473), 'The Diplomat Hotel', 'movie')])
        self.assertEqual('Delivery Boi', db.get(2473)[0]['name'])
        self.assertEqual(('The Diplomat Hotel', 'movie'), (db.get(movies.toMovieId(2473))[0]['name'], db.get(movies.toMovieId(2473))[0]['ltype']))
        # the counters of the two are kept apart
        db.update({'id': movies.toMovieId(2473), 'views': 3})
        self.assertEqual([0, 3], [db.get(2473)[0]['views'], db.get(movies.toMovieId(2473))[0]['views']])

    def test_search_the_shows(self):
        d = tempfile.mkdtemp()
        db = shows.Show(os.path.join(d, 'shows.db'))
        db._userdata = userdata.UserData(os.path.join(d, 'userdata.db'))
        db.set([show(2473, 'Delivery Boi'), show(movies.toMovieId(2473), 'The Diplomat Hotel (2013)', 'movie'), show(5, 'Another')])
        self.assertEqual(['The Diplomat Hotel (2013)'], [s['name'] for s in db.searchByTitle('diplomat')])
        self.assertEqual(['Another', 'Delivery Boi', 'The Diplomat Hotel (2013)'], [s['name'] for s in db.searchByYear('2026')])
        self.assertEqual(3, len(db.searchByCategory('Drama')))


if __name__ == '__main__':
    unittest.main()
