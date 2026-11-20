# -*- coding: utf-8 -*-
"""Ids of the movies and of the public affairs shows, search in the shows: python -m unittest discover -s tests"""

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

from resources import config  # noqa: E402
from resources.lib.libraries import origins  # noqa: E402
from resources.lib.models import episodes, shows, userdata  # noqa: E402


def show(i, name, ltype='show'):
    return {'id': i, 'name': name, 'parentid': -1, 'parentname': 'Drama', 'logo': 'l', 'image': 'i', 'fanart': 'f',
            'banner': 'b', 'url': 'u', 'description': 'd', 'shortdescription': 'd', 'year': '2026', 'ltype': ltype,
            'duration': 0, 'views': 0, 'rating': 0, 'votes': 0}


class OriginsTest(unittest.TestCase):

    def test_ids(self):
        for plain in (2473, '331122', None, 'x'):
            self.assertEqual('', origins.originOfId(plain))
        movie, pa = origins.toStoredId('fulleps', '2473'), origins.toStoredId('pa', 2473)
        self.assertEqual(['fulleps', 'pa'], [origins.originOfId(movie), origins.originOfId(pa)])
        self.assertEqual(3, len(set([2473, movie, pa])))
        self.assertEqual([2473, 2473, 2473, 2473], [origins.toApiId(2473), origins.toApiId(movie), origins.toApiId(str(pa)), origins.toStoredId('', 2473)])

    def test_the_offsets_leave_room_for_the_ids(self):
        offsets = sorted(c['offset'] for c in config.catalogs.values())
        self.assertGreater(offsets[0], 100000000)      # far above the ids of the shows and of their episodes
        self.assertGreater(offsets[1] - offsets[0], 100000000)

    def test_origin_of_a_show(self):
        self.assertEqual(['fulleps', 'pa', '', '', ''], [origins.originOfShow({'origin': o}) for o in ('fulleps', 'pa', 'ent', 'other', None)] )
        self.assertEqual('', origins.originOfShow({}))

    def test_services_and_images(self):
        self.assertEqual('/entertainment/tv/pa/%s/show_details.gz', origins.service('pa', 'details', 'default'))
        self.assertEqual('tracker/pa', origins.service('pa', 'nbPages', 'default')[len('/entertainment/'):len('/entertainment/tracker/pa')])
        self.assertEqual('default', origins.service('', 'details', 'default'))
        self.assertEqual(['entertainment', 'fulleps', 'gno'], [origins.imageSection(o) for o in ('', 'fulleps', 'pa')])

    def test_ltype(self):
        self.assertEqual('movie', origins.ltype('fulleps', 1))
        self.assertEqual('show', origins.ltype('fulleps', 8))   # a series of the movies catalog
        self.assertEqual('show', origins.ltype('fulleps', 0))
        self.assertEqual('show', origins.ltype('', 1))          # a show with one episode so far is not a movie
        self.assertEqual('show', origins.ltype('pa', 1))

    def test_a_show_and_a_movie_with_the_same_website_id_can_be_stored(self):
        d = tempfile.mkdtemp()
        db = shows.Show(os.path.join(d, 'shows.db'))
        db._userdata = userdata.UserData(os.path.join(d, 'userdata.db'))
        db.set([show(2473, 'Delivery Boi'), show(origins.toStoredId('fulleps', 2473), 'The Diplomat Hotel', 'movie')])
        self.assertEqual('Delivery Boi', db.get(2473)[0]['name'])
        self.assertEqual(('The Diplomat Hotel', 'movie'), (db.get(origins.toStoredId('fulleps', 2473))[0]['name'], db.get(origins.toStoredId('fulleps', 2473))[0]['ltype']))
        # a public affairs show with the same website id too
        pa = origins.toStoredId('pa', 2473)
        db.set([show(pa, 'Wish Ko Lang')])
        self.assertEqual(['Delivery Boi', 'Wish Ko Lang'], [db.get(2473)[0]['name'], db.get(pa)[0]['name']])
        # the counters of the two are kept apart
        db.update({'id': origins.toStoredId('fulleps', 2473), 'views': 3})
        self.assertEqual([0, 3], [db.get(2473)[0]['views'], db.get(origins.toStoredId('fulleps', 2473))[0]['views']])

    def test_search_the_shows(self):
        d = tempfile.mkdtemp()
        db = shows.Show(os.path.join(d, 'shows.db'))
        db._userdata = userdata.UserData(os.path.join(d, 'userdata.db'))
        db.set([show(2473, 'Delivery Boi'), show(origins.toStoredId('fulleps', 2473), 'The Diplomat Hotel (2013)', 'movie'), show(5, 'Another')])
        self.assertEqual(['The Diplomat Hotel (2013)'], [s['name'] for s in db.searchByTitle('diplomat')])
        self.assertEqual(['Another', 'Delivery Boi', 'The Diplomat Hotel (2013)'], [s['name'] for s in db.searchByYear('2026')])
        self.assertEqual(3, len(db.searchByCategory('Drama')))

    def test_fix_the_types_stored_by_the_first_reloads(self):
        d = tempfile.mkdtemp()
        showsPath, episodesPath = os.path.join(d, 'shows.db'), os.path.join(d, 'episodes.db')
        showDB, episodeDB = shows.Show(showsPath), episodes.Episode(episodesPath)
        showDB._userdata = episodeDB._userdata = userdata.UserData(os.path.join(d, 'userdata.db'))
        one, series, regular = origins.toStoredId('fulleps', 1), origins.toStoredId('fulleps', 2), 7
        showDB.set([show(one, 'A film', 'movie'), show(series, 'A series', 'movie'), show(regular, 'A show')])

        def episode(i, showId, ltype):
            return {'id': i, 'title': 'E%d' % i, 'parentid': showId, 'show': 'S', 'image': 'i', 'fanart': 'f', 'episodenumber': i,
                    'url': 'u', 'description': 'd', 'shortdescription': 'd', 'date': '2026-01-02', 'year': '2026',
                    'parentalAdvisory': 'G', 'ltype': ltype, 'duration': 0, 'views': 0, 'rating': 0, 'votes': 0}
        episodeDB.set([episode(origins.toStoredId('fulleps', 10), one, 'movie'), episode(origins.toStoredId('fulleps', 11), series, 'movie'),
                       episode(origins.toStoredId('fulleps', 12), series, 'movie'), episode(13, regular, 'show')])
        self.assertEqual(1, origins.fixTypes(showsPath, episodesPath))
        self.assertEqual(['movie', 'show', 'show'], [showDB.get(i)[0]['ltype'] for i in (one, series, regular)])
        self.assertEqual(['movie', 'show', 'show', 'show'], [episodeDB.get(i)[0]['ltype'] for i in (origins.toStoredId('fulleps', 10), origins.toStoredId('fulleps', 11), origins.toStoredId('fulleps', 12), 13)])
        self.assertEqual(0, origins.fixTypes(showsPath, episodesPath))  # nothing left to fix

    def test_fix_the_types_without_databases(self):
        d = tempfile.mkdtemp()
        self.assertEqual(0, origins.fixTypes(os.path.join(d, 'a.db'), os.path.join(d, 'b.db')))


if __name__ == '__main__':
    unittest.main()
