# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

from resources.lib.models import model
from resources.lib.models import userdata
from resources.lib.libraries import control

logger = control.logger

class Show(model.Model):
    
    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 17:
            return {
                'id' : int(data[0]),
                'name' : data[1],
                'parentid' : int(data[2]),
                'parentname' : data[3],
                'logo' : data[4],
                'image' : data[5],
                'fanart' : data[6],
                'banner' : data[7],
                'url' : data[8],
                'description' : data[9],
                'shortdescription' : data[10],
                'year' : data[11],
                'ltype' : data[12],
                'duration' : int(data[13]),
                'views' : int(data[14]),
                'rating' : int(data[15]),
                'votes' : int(data[16]),
                'type' : 'show'
                }
        return {}
    
    def _applyUserData(self, items):
        """The counters come from the user data database"""
        if not items:
            return items
        stats = self.getUserData().getStats(userdata.SHOW, [item['id'] for item in items if item.get('id') is not None])
        for item in items:
            item['views'], item['rating'], item['votes'] = stats.get(str(item.get('id')), (0, 0, 0))
        return items

    def _saveUserData(self, data):
        """Store the user data fields (views, rating, votes) of an item"""
        self.getUserData().setStats(userdata.SHOW, data['id'], data.get('views'), data.get('rating'), data.get('votes'))

    def _search(self, search, sort, limit):
        dbcur = self.getCursor()
        where, params = self._where(search)
        sortBy = self._sortBy(sort)
        first = 'LIMIT %d' % int(limit) if limit != False else ''
        dbcur.execute(logger.logDebug("SELECT ID, \
            TITLE, \
            PARENTID, \
            PARENTNAME, \
            THUMBNAIL, \
            IMAGE, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            YEAR, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES \
            FROM SHOW \
            WHERE %s %s %s" % (where, sortBy, first)), params)
        return logger.logDebug(dbcur.fetchall())

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            TITLE, \
            PARENTID, \
            PARENTNAME, \
            THUMBNAIL, \
            IMAGE, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            YEAR, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES \
            FROM SHOW"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            TITLE, \
            PARENTID, \
            PARENTNAME, \
            THUMBNAIL, \
            IMAGE, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            SHORTDESCRIPTION, \
            YEAR, \
            TYPE, \
            DURATION, \
            VIEWS, \
            RATING, \
            VOTES \
            FROM SHOW \
            WHERE %s IN (%s)" % (self._column(key), self._marks(mixed))), list(mixed))
        return logger.logDebug(dbcur.fetchall())

    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._saveUserData(data)
                self._update(dbcur, 'SHOW', [
                    ('TITLE', data.get('name')),
                    ('PARENTID', data.get('parentid')),
                    ('PARENTNAME', data.get('parentname')),
                    ('THUMBNAIL', data.get('logo')),
                    ('FANART', data.get('image')),
                    ('IMAGE', data.get('fanart')),
                    ('BANNER', data.get('banner')),
                    ('URL', data.get('url')),
                    ('DESCRIPTION', data.get('description')),
                    ('SHORTDESCRIPTION', data.get('shortdescription')),
                    ('YEAR', data.get('year')),
                    ('TYPE', data.get('ltype')),
                    ('DURATION', data.get('duration')),
                    ], data.get('id'))
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            dbcur.execute(logger.logDebug("DELETE FROM SHOW WHERE ID in (%s)" % self._marks(ids)), ids)
            for data in mixed:
                dbcur.execute("INSERT INTO SHOW VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id'), 
                    data.get('name'), 
                    data.get('parentid'), 
                    data.get('parentname'), 
                    data.get('logo').replace('&#39;', '\''), 
                    data.get('image').replace('&#39;', '\''), 
                    data.get('fanart').replace('&#39;', '\''), 
                    data.get('banner').replace('&#39;', '\''), 
                    data.get('url'), 
                    data.get('description'), 
                    data.get('shortdescription'), 
                    data.get('year'), 
                    data.get('ltype'), 
                    data.get('duration', 0), 
                    0, 
                    0, 
                    0))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        ids = []
        logger.logDebug(mixed)
        for data in mixed:
            if 'id' in data:
                ids.append(str(data.get('id')))
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                dbcur.execute(logger.logDebug("DELETE FROM SHOW WHERE ID in (%s)" % self._marks(ids)), ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE SHOW"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def searchByTitle(self, title, limit=100):
        return self.search({'TITLE' : title}, ['TITLE', 'ASC'], limit)

    def searchByCategory(self, category, limit=100):
        return self.search({'PARENTNAME' : category}, ['TITLE', 'ASC'], limit)

    def searchByYear(self, year, limit=100):
        return self.search({'YEAR' : year}, ['TITLE', 'ASC'], limit)

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS SHOW (\
            ID INTEGER PRIMARY KEY, \
            TITLE TEXT, \
            PARENTID INTEGER, \
            PARENTNAME TEXT, \
            THUMBNAIL TEXT, \
            IMAGE TEXT, \
            FANART TEXT, \
            BANNER TEXT, \
            URL TEXT, \
            DESCRIPTION TEXT, \
            SHORTDESCRIPTION TEXT, \
            YEAR TEXT, \
            TYPE TEXT, \
            DURATION INTEGER NOT NULL DEFAULT 0, \
            VIEWS INTEGER NOT NULL DEFAULT 0, \
            RATING INTEGER NOT NULL DEFAULT 0, \
            VOTES INTEGER NOT NULL DEFAULT 0)"))
        self._dbcon.commit()
        return True
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM SHOW"))
        stats['count'] = dbcur.fetchone()
        return stats


