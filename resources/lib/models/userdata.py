# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

import os
import re
import time

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

SHOW = 'show'
EPISODE = 'episode'


def isNewEpisode(episodeId, aired, last):
    """Whether the last episode of a show (id, air date YYYY-MM-DD) is new compared to what My List knows
    of it (`last`: seen episode id, its air date, notified episode id). Nothing is new the first time (no seen
    episode yet), and an older episode that became the last one (the newest was removed) is not new."""
    seen, seenAired = (last or (None, None, None))[:2]
    if not seen or str(episodeId) == str(seen):
        return False
    isDate = lambda text: bool(re.match(r'\d{4}-\d{2}-\d{2}', str(text or '')))
    if isDate(aired) and isDate(seenAired) and str(aired)[:10] < str(seenAired)[:10]:
        return False
    return True


class UserData(model.Model):
    """Data that belongs to the user (My List, views, rating, view history, META), kept apart from the catalog
    databases (shows, episodes) so that refreshing, resetting or replacing the catalog never loses it."""

    # max values per "IN (...)" (SQLite older than 3.32 accepts 999 variables)
    _chunkSize = 500

    # the oldest views are dropped beyond this
    historyLimit = 2000

    def __init__(self, databasePath):
        model.Model.__init__(self, databasePath)
        self.checkIfTablesExist()

    def _exec(self, dbcur, sql, params=()):
        logger.logDebug('%s %s' % (sql, repr(params)))
        return dbcur.execute(sql, params)

    def checkIfTablesExist(self):
        dbcur = self.getCursor()
        for sql in (
            "CREATE TABLE IF NOT EXISTS STATS (\
                KIND TEXT NOT NULL, \
                ITEMID TEXT NOT NULL, \
                VIEWS INTEGER NOT NULL DEFAULT 0, \
                RATING INTEGER NOT NULL DEFAULT 0, \
                VOTES INTEGER NOT NULL DEFAULT 0, \
                PRIMARY KEY (KIND, ITEMID))",
            "CREATE TABLE IF NOT EXISTS META (\
                KEY TEXT PRIMARY KEY, \
                VALUE TEXT)",
            "CREATE TABLE IF NOT EXISTS HISTORY (\
                ID INTEGER PRIMARY KEY AUTOINCREMENT, \
                EPISODEID TEXT NOT NULL, \
                SHOWID TEXT, \
                TITLE TEXT, \
                SHOWNAME TEXT, \
                THUMBNAIL TEXT, \
                LTYPE TEXT, \
                VIEWED TEXT)",
            "CREATE INDEX IF NOT EXISTS HISTORY_EPISODE ON HISTORY (EPISODEID)",
            "CREATE TABLE IF NOT EXISTS MYLIST (\
                SHOWID TEXT PRIMARY KEY, \
                TITLE TEXT, \
                ADDED TEXT)"
        ):
            self._exec(dbcur, sql)
        # 2.2: the last episode of each show, as listed by My Shows Last Episodes (SEEN) and as notified (NOTIFIED)
        columns = [r[1].upper() for r in self._exec(dbcur, 'PRAGMA table_info(MYLIST)').fetchall()]
        for column in ('SEENEPISODE', 'SEENAIRED', 'NOTIFIEDEPISODE'):
            if column not in columns:
                self._exec(dbcur, 'ALTER TABLE MYLIST ADD COLUMN %s TEXT' % column)
        self._dbcon.commit()

    # --- meta

    def getMeta(self, key, default=None):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT VALUE FROM META WHERE KEY = ?', (key,))
        row = dbcur.fetchone()
        return default if row is None else row[0]

    def setMeta(self, key, value):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM META WHERE KEY = ?', (key,))
        self._exec(dbcur, 'INSERT INTO META (KEY, VALUE) VALUES (?, ?)', (key, str(value)))
        self._dbcon.commit()

    def deleteMeta(self, prefix):
        """Forget the META entries whose key starts with `prefix`"""
        dbcur = self.getCursor()
        self._exec(dbcur, "DELETE FROM META WHERE KEY LIKE ? ESCAPE '\\'", (prefix.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%',))
        self._dbcon.commit()

    # --- My List: the shows the user follows (the ids of the catalog databases)

    def addToMyList(self, showId, title=''):
        dbcur = self.getCursor()
        self._exec(dbcur, 'INSERT OR REPLACE INTO MYLIST (SHOWID, TITLE, ADDED) VALUES (?, ?, ?)',
                   (str(showId), title or '', time.strftime('%Y-%m-%d %H:%M:%S')))
        self._dbcon.commit()
        return True

    def removeFromMyList(self, showId):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM MYLIST WHERE SHOWID = ?', (str(showId),))
        self._dbcon.commit()
        return dbcur.rowcount > 0

    def getMyList(self):
        """The (show id, title) pairs of My List, the last added first"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT SHOWID, TITLE FROM MYLIST ORDER BY ADDED DESC, ROWID DESC')
        return [(r[0], r[1]) for r in dbcur.fetchall()]

    def getMyListIds(self):
        return [r[0] for r in self.getMyList()]

    def getMyListLastEpisodes(self):
        """{show id: (seen episode id, its air date, notified episode id)} of the shows of My List"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT SHOWID, SEENEPISODE, SEENAIRED, NOTIFIEDEPISODE FROM MYLIST')
        return dict((r[0], (r[1], r[2], r[3])) for r in dbcur.fetchall())

    def setMyListSeenEpisode(self, showId, episodeId, aired=''):
        """The last episode of a show was listed (it is then not notified anymore)"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'UPDATE MYLIST SET SEENEPISODE = ?, SEENAIRED = ?, NOTIFIEDEPISODE = ? WHERE SHOWID = ?',
                   (str(episodeId), aired or '', str(episodeId), str(showId)))
        self._dbcon.commit()
        return dbcur.rowcount > 0

    def setMyListNotifiedEpisode(self, showId, episodeId):
        dbcur = self.getCursor()
        self._exec(dbcur, 'UPDATE MYLIST SET NOTIFIEDEPISODE = ? WHERE SHOWID = ?', (str(episodeId), str(showId)))
        self._dbcon.commit()
        return dbcur.rowcount > 0

    # --- views, rating, votes

    def getStats(self, kind, ids):
        """{id: (views, rating, votes)} for the ids that have stored stats (the ids are strings)"""
        ids = [str(i) for i in ids]
        dbcur = self.getCursor()
        stats = {}
        for i in range(0, len(ids), self._chunkSize):
            chunk = ids[i:i + self._chunkSize]
            self._exec(dbcur, 'SELECT ITEMID, VIEWS, RATING, VOTES FROM STATS WHERE KIND = ? AND ITEMID IN (%s)' % ','.join('?' * len(chunk)),
                       [str(kind)] + chunk)
            for r in dbcur.fetchall():
                stats[r[0]] = (int(r[1]), int(r[2]), int(r[3]))
        return stats

    def setStats(self, kind, itemId, views=None, rating=None, votes=None):
        """Store the given counters of an item (the others are kept)"""
        values = [('VIEWS', views), ('RATING', rating), ('VOTES', votes)]
        values = [(c, int(v)) for c, v in values if v is not None]
        if not values:
            return False
        dbcur = self.getCursor()
        self._exec(dbcur, 'UPDATE STATS SET %s WHERE KIND = ? AND ITEMID = ?' % ', '.join('%s = ?' % c for c, v in values),
                   [v for c, v in values] + [str(kind), str(itemId)])
        if dbcur.rowcount < 1:
            fields = dict(values)
            self._exec(dbcur, 'INSERT INTO STATS (KIND, ITEMID, VIEWS, RATING, VOTES) VALUES (?, ?, ?, ?, ?)',
                       (str(kind), str(itemId), fields.get('VIEWS', 0), fields.get('RATING', 0), fields.get('VOTES', 0)))
        self._dbcon.commit()
        return True

    def getViews(self, kind, itemId):
        """How many times an item was played"""
        return self.getStats(kind, [itemId]).get(str(itemId), (0, 0, 0))[0]

    # --- view history: what the user played, with what is needed to list it even when the catalog is replaced

    def addToHistory(self, episodeId, showId='', title='', show='', thumbnail='', ltype='', viewed=None):
        """Record a view of an episode"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'INSERT INTO HISTORY (EPISODEID, SHOWID, TITLE, SHOWNAME, THUMBNAIL, LTYPE, VIEWED) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (str(episodeId), str(showId or ''), title or '', show or '', thumbnail or '', ltype or '',
                    time.strftime('%Y-%m-%d %H:%M:%S') if viewed is None else viewed))
        self._exec(dbcur, 'DELETE FROM HISTORY WHERE ID <= (SELECT ID FROM HISTORY ORDER BY ID DESC LIMIT 1 OFFSET ?)', (self.historyLimit,))
        self._dbcon.commit()
        return True

    def getHistory(self, limit=100, offset=0):
        """The episodes viewed, the last viewed first; an episode viewed several times is listed once (its last view)"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT EPISODEID, SHOWID, TITLE, SHOWNAME, THUMBNAIL, LTYPE, VIEWED FROM HISTORY '
                          'WHERE ID IN (SELECT MAX(ID) FROM HISTORY GROUP BY EPISODEID) '
                          'ORDER BY VIEWED DESC, ID DESC LIMIT ? OFFSET ?', (int(limit), int(offset)))
        return [{'episodeid': r[0], 'showid': r[1], 'title': r[2], 'show': r[3], 'thumbnail': r[4], 'ltype': r[5], 'viewed': r[6]}
                for r in dbcur.fetchall()]

    def countHistory(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'SELECT COUNT(DISTINCT EPISODEID) FROM HISTORY')
        return dbcur.fetchone()[0]

    def removeFromHistory(self, episodeId):
        """Forget an episode: it isn't listed anymore and its view count goes with it"""
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM HISTORY WHERE EPISODEID = ?', (str(episodeId),))
        self._exec(dbcur, 'UPDATE STATS SET VIEWS = 0 WHERE KIND = ? AND ITEMID = ?', (EPISODE, str(episodeId)))
        self._dbcon.commit()
        return True

    def clearHistory(self):
        dbcur = self.getCursor()
        self._exec(dbcur, 'DELETE FROM HISTORY')
        self._exec(dbcur, 'UPDATE STATS SET VIEWS = 0 WHERE KIND = ?', (EPISODE,))
        self._dbcon.commit()
        return True

    # --- one-time import of what the previous versions stored in the catalog databases

    def importLegacy(self, showsPath, episodesPath):
        """Move the counters (views, rating, votes) stored in the SHOW/EPISODE columns of the catalog
        databases of the previous versions here. Done once. Returns the number of imported rows."""
        if self.getMeta('legacyImported') == '1':
            return 0
        count = self._importLegacyTable(showsPath, 'SHOW', SHOW) + self._importLegacyTable(episodesPath, 'EPISODE', EPISODE)
        self.setMeta('legacyImported', 1)
        logger.logNotice('User data imported from the catalog databases: %d rows' % count)
        return count

    def _importLegacyTable(self, path, table, kind):
        count = 0
        if not os.path.exists(path):
            return 0
        try:
            legacy = database.connect(path)
        except Exception as e:
            logger.logError('Can\'t open %s: %s' % (path, str(e)))
            return 0
        try:
            cur = legacy.cursor()
            columns = [r[1].upper() for r in cur.execute('PRAGMA table_info(%s)' % table).fetchall()]
            if all(c in columns for c in ('VIEWS', 'RATING', 'VOTES')):
                dbcur = self.getCursor()
                for row in cur.execute('SELECT ID, VIEWS, RATING, VOTES FROM %s WHERE VIEWS > 0 OR RATING > 0 OR VOTES > 0' % table).fetchall():
                    self._exec(dbcur, 'INSERT OR IGNORE INTO STATS (KIND, ITEMID, VIEWS, RATING, VOTES) VALUES (?, ?, ?, ?, ?)',
                               (kind, str(row[0]), int(row[1] or 0), int(row[2] or 0), int(row[3] or 0)))
                    count += 1
                self._dbcon.commit()
        except Exception as e:
            logger.logError('Can\'t import the user data of %s: %s' % (table, str(e)))
        finally:
            legacy.close()
        return count
