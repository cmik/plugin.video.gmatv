# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

import re
import sqlite3

# an image URL built from an empty image name ('.../shows/images/640_480_'), stored by the versions before 2.0.0~dev2
EMPTY_IMAGE = re.compile(r'/\d+_\d+_$')

# the image columns of the catalog tables, in the order a missing image is replaced from
IMAGE_COLUMNS = {
    'SHOW' : ('THUMBNAIL', 'IMAGE', 'FANART', 'BANNER'),
    'EPISODE' : ('THUMBNAIL', 'FANART'),
    'SHOW_CAST' : ('THUMBNAIL',),
    }


def isEmptyImage(url):
    return not url or bool(EMPTY_IMAGE.search(url))


def fixEmptyImages(dbPath, table):
    """Replace in `table` the image URLs without an image name by another image of the same row (or ''),
    so that Kodi stops asking for them (HTTP 404). Returns the number of rows changed."""
    columns = IMAGE_COLUMNS[table]
    changed = 0
    try:
        con = sqlite3.connect(dbPath)
        try:
            rows = con.execute('SELECT ID, %s FROM %s' % (', '.join(columns), table)).fetchall()
            for row in rows:
                values = list(row[1:])
                if not any(v and EMPTY_IMAGE.search(v) for v in values):
                    continue
                fallback = next((v for v in values if not isEmptyImage(v)), '')
                fixed = [fallback if isEmptyImage(v) else v for v in values]
                con.execute('UPDATE %s SET %s WHERE ID = ?' % (table, ', '.join('%s = ?' % c for c in columns)), fixed + [row[0]])
                changed += 1
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        # no table yet (new installation): nothing to fix
        return 0
    return changed
