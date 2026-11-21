# -*- coding: utf-8 -*-
"""Fix of the image URLs stored without an image name"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resources.lib.libraries import dbfixes  # noqa: E402

BASE = 'https://aphrodite.gmanetwork.com/entertainment/shows/images/'


class DbFixesTest(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), 'shows.db')
        con = sqlite3.connect(self.path)
        con.execute('CREATE TABLE SHOW (ID INTEGER PRIMARY KEY, THUMBNAIL TEXT, IMAGE TEXT, FANART TEXT, BANNER TEXT)')
        con.executemany('INSERT INTO SHOW VALUES (?, ?, ?, ?, ?)', [
            (1, BASE + '640_480_a.jpg', BASE + '640_480_', BASE + '1867_1050_b.jpg', BASE + '1867_1050_b.jpg'),
            (2, BASE + '640_480_', BASE + '640_480_', BASE + '1867_1050_', BASE + '1867_1050_'),
            (3, BASE + '640_480_c.jpg', BASE + '640_480_c.jpg', BASE + '1867_1050_c.jpg', BASE + '1867_1050_c.jpg'),
            ])
        con.commit()
        con.close()

    def rows(self):
        con = sqlite3.connect(self.path)
        try:
            return dict((r[0], r[1:]) for r in con.execute('SELECT * FROM SHOW'))
        finally:
            con.close()

    def test_empty_images_are_replaced(self):
        before = self.rows()
        self.assertEqual(2, dbfixes.fixEmptyImages(self.path, 'SHOW'))
        after = self.rows()
        self.assertEqual((BASE + '640_480_a.jpg', BASE + '640_480_a.jpg', BASE + '1867_1050_b.jpg', BASE + '1867_1050_b.jpg'), after[1])
        self.assertEqual(('', '', '', ''), after[2])
        self.assertEqual(before[3], after[3])
        # a second run has nothing left to do
        self.assertEqual(0, dbfixes.fixEmptyImages(self.path, 'SHOW'))

    def test_no_table(self):
        self.assertEqual(0, dbfixes.fixEmptyImages(os.path.join(tempfile.mkdtemp(), 'none.db'), 'EPISODE'))


if __name__ == '__main__':
    unittest.main()
