# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

class ShowCast(model.Model):
    
    idFormat = '%d-%d'

    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 8:
            return {
                'id' : data[0],
                'showid' : int(data[1]),
                'actorid' : int(data[2]),
                'name' : data[3],
                'role' : data[4],
                'thumbnail' : data[5],
                'order' : data[6],
                'castUrl' : data[7]
                }
        return {}
    
    def _search(self, search, sort, limit):
        dbcur = self.getCursor()
        where, params = self._where(search)
        sortBy = self._sortBy(sort)
        first = 'LIMIT %d' % int(limit) if limit != False else ''
        dbcur.execute(logger.logDebug("SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL \
            FROM SHOW_CAST \
            WHERE %s %s %s" % (where, sortBy, first)), params)
        return logger.logDebug(dbcur.fetchall())

    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL \
            FROM SHOW_CAST"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            SHOWID, \
            ACTORID, \
            NAME, \
            ROLE, \
            THUMBNAIL, \
            ORDR, \
            URL \
            FROM SHOW_CAST \
            WHERE %s IN (%s)" % (self._column(key), self._marks(mixed))), list(mixed))
        return logger.logDebug(dbcur.fetchall())

    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'id' in data or ('showid' in data and 'castid' in data):
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._update(dbcur, 'SHOW_CAST', [
                    ('SHOWID', data.get('showid')),
                    ('ACTORID', data.get('castid')),
                    ('NAME', data.get('name')),
                    ('ROLE', data.get('role')),
                    ('THUMBNAIL', data.get('thumbnail')),
                    ('ORDR', data.get('order')),
                    ('URL', data.get('url')),
                    ], data.get('id', self.idFormat % (data.get('showid'), data.get('castid'))))
        self._dbcon.commit()
        return True

    def _replace(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data.get('id', self.idFormat % (data.get('showid'), data.get('castid')))) for data in mixed if 'id' in data or ('showid' in data and 'castid' in data)]
        if len(ids) > 0:
            self.checkIfTableExists()
            dbcur = self.getCursor()
            dbcur.execute('PRAGMA encoding="UTF-8";')
            dbcur.execute(logger.logDebug("DELETE FROM SHOW_CAST WHERE ID in (%s)" % self._marks(ids)), ids)
            for data in mixed:
                dbcur.execute("INSERT INTO SHOW_CAST VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id', self.idFormat % (data.get('showid'), data.get('castid'))), 
                    data.get('showid'), 
                    data.get('castid'), 
                    data.get('name'), 
                    data.get('role'), 
                    data.get('thumbnail').replace('&#39;', '\''), 
                    data.get('order'), 
                    data.get('url')))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data.get('id', self.idFormat % (data.get('showid'), data.get('castid')))) for data in mixed if 'id' in data or ('showid' in data and 'castid' in data)]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                dbcur.execute(logger.logDebug("DELETE FROM SHOW_CAST WHERE ID in (%s)" % self._marks(ids)), ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE SHOW_CAST"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def getByShow(self, mixed, limit=100):
        return self.get(mixed, 'SHOWID')

    def searchByActorName(self, name, limit=100):
        return self.search({'NAME' : name}, ['NAME', 'ASC'], limit)

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS SHOW_CAST (\
            ID TEXT PRIMARY KEY, \
            SHOWID INTEGER, \
            ACTORID INTEGER, \
            NAME TEXT, \
            ROLE TEXT, \
            THUMBNAIL TEXT, \
            ORDR INTEGER, \
            URL TEXT)"))
        return self._dbcon.commit()
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM SHOW_CAST"))
        stats['count'] = dbcur.fetchone()
        return stats