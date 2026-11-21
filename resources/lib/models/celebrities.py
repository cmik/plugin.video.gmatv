# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

from resources.lib.models import model
from resources.lib.libraries import control

logger = control.logger

class Actor(model.Model):
    
    def _getStructure(self, data):
        logger.logDebug(len(data))
        logger.logDebug(data)
        if len(data) == 9:
            return {
                'id' : int(data[0]),
                'name' : data[1],
                'thumbnail' : data[2],
                'fanart' : data[3],
                'banner' : data[4],
                'url' : data[5],
                'description' : data[6],
                'birthday' : data[7],
                'birthplace' : data[8]
                }
        return {}
         
    def _retrieveAll(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            NAME, \
            THUMBNAIL, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            BIRTHDAY, \
            BIRTHPLACE \
            FROM ACTOR"))
        return logger.logDebug(dbcur.fetchall())
         
    def _retrieve(self, mixed, key):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT ID, \
            NAME, \
            THUMBNAIL, \
            FANART, \
            BANNER, \
            URL, \
            DESCRIPTION, \
            BIRTHDAY, \
            BIRTHPLACE \
            FROM ACTOR \
            WHERE %s IN (%s)" % (self._column(key), self._marks(mixed))), list(mixed))
        return logger.logDebug(dbcur.fetchall())
        
    def _save(self, mixed):
        logger.logDebug(mixed)
        self.checkIfTableExists()
        for data in mixed:
            if 'id' in data:
                dbcur = self.getCursor()
                dbcur.execute('PRAGMA encoding="UTF-8";')
                self._update(dbcur, 'ACTOR', [
                    ('NAME', data.get('name')),
                    ('THUMBNAIL', data.get('logo')),
                    ('FANART', data.get('image')),
                    ('BANNER', data.get('banner')),
                    ('URL', data.get('url')),
                    ('DESCRIPTION', data.get('description')),
                    ('BIRTHDAY', data.get('birthday')),
                    ('BIRTHPLACE', data.get('birthplace')),
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
            dbcur.execute(logger.logDebug("DELETE FROM ACTOR WHERE ID in (%s)" % self._marks(ids)), ids)
            for data in mixed:
                dbcur.execute("INSERT INTO ACTOR VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    data.get('id'), 
                    data.get('name'), 
                    data.get('thumbnail').replace('&#39;', '\''), 
                    data.get('fanart').replace('&#39;', '\''), 
                    data.get('banner').replace('&#39;', '\''), 
                    data.get('url'), 
                    data.get('description'), 
                    data.get('birthday'), 
                    data.get('birthplace')))
            self._dbcon.commit()
            return True
        return False

    def _remove(self, mixed):
        logger.logDebug(mixed)
        ids = [str(data['id']) for data in mixed if 'id' in data]
        if len(ids) > 0:
            dbcur = self.getCursor()
            try: 
                dbcur.execute(logger.logDebug("DELETE FROM ACTOR WHERE ID in (%s)" % self._marks(ids)), ids)
                self._dbcon.commit()
                return True
            except: pass
        return False

    def _drop(self):
        dbcur = self.getCursor()
        try: 
            dbcur.execute(logger.logDebug("DROP TABLE ACTOR"))
            self._dbcon.commit()
            return True
        except: 
            return False

    def checkIfTableExists(self):
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("CREATE TABLE IF NOT EXISTS ACTOR (\
            ID INTEGER PRIMARY KEY, \
            NAME TEXT, \
            THUMBNAIL TEXT, \
            FANART TEXT, \
            BANNER TEXT, \
            URL TEXT, \
            DESCRIPTION TEXT, \
            BIRTHDAY TEXT, \
            BIRTHPLACE TEXT)"))
        return self._dbcon.commit()
            
    def getStatistics(self):
        stats = {}
        dbcur = self.getCursor()
        dbcur.execute(logger.logDebug("SELECT COUNT(*) FROM ACTOR"))
        stats['count'] = dbcur.fetchone()
        return stats