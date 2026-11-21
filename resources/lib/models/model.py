# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

import re

from resources.lib.libraries import control
logger = control.logger
    
class Model():
    
    _dbcon = None
    # user data (views, rating, votes...) lives in a separate database
    _userdata = None

    def __init__(self, databasePath):
        self._dbcon = database.connect(logger.logDebug(databasePath))
        return None
        
    def _getStructure(self, data):
        return {}

    def getUserData(self):
        """The user data database (created on first use)"""
        if self._userdata is None:
            from resources.lib.models import userdata
            self._userdata = userdata.UserData(control.userDataFile)
        return self._userdata

    def applyUserData(self, items):
        """Add the user data to items that didn't come from this model's reads"""
        return self._applyUserData(items)

    def _applyUserData(self, items):
        """Add the user data to the items read from the database (models override it)"""
        return items
        
    def _search(self, sort, limit):
        return []

    def _retrieveAll(self):
        return []
        
    def _retrieve(self, mixed):
        return []
        
    def _save(self, mixed):
        return False        

    def _replace(self, mixed):
        return False
       
    def getCursor(self):
        return self._dbcon.cursor()

    # The values always go to SQLite as parameters (a title like "It's Showtime" broke the
    # queries built by hand); only the column names, which come from the code, are written in the SQL.
    @staticmethod
    def _column(name):
        name = str(name)
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
            raise ValueError('invalid column name %r' % name)
        return name

    @staticmethod
    def _marks(values):
        """The placeholders of an IN (...) list"""
        return ','.join('?' * len(values))

    def _where(self, search):
        """The WHERE clause and its parameters of a search {column: text contained}"""
        where = []
        params = []
        for k, v in search.items():
            where.append('%s LIKE ?' % self._column(k))
            params.append('%%%s%%' % v)
        return ' AND '.join(where), params

    def _sortBy(self, sort):
        if sort == False:
            return ''
        direction = str(sort[1]).upper() if len(sort) > 1 else 'ASC'
        if direction not in ('ASC', 'DESC'):
            raise ValueError('invalid sort direction %r' % direction)
        return 'ORDER BY %s %s' % (self._column(sort[0]), direction)

    def _update(self, dbcur, table, columns, itemId):
        """Update the columns of [(column, value)] that have a value, the others keep theirs"""
        sets = []
        params = []
        for column, value in columns:
            if value:
                sets.append('%s = ?' % self._column(column))
                params.append(value)
        if sets:
            dbcur.execute(logger.logDebug('UPDATE %s SET %s WHERE ID = ?' % (self._column(table), ', '.join(sets))), params + [itemId])
    
    def search(self, search, sort=False, limit=False):
        items = []
        if isinstance(search, dict):
            try:
                results = self._search(search, sort, limit)
                for d in results:
                    items.append(self._getStructure(d))
                items = self._applyUserData(items)
            except (Exception) as e:
                logger.logError('Exception: %s for data %s' % (str(e), repr(search)))
                pass

        return items

    def getAll(self):
        items = []
        try:
            results = self._retrieveAll()
            for d in results:
                items.append(self._getStructure(d))
            items = self._applyUserData(items)
        except (Exception) as e:
            logger.logError('Exception: %s' % str(e))
            pass

        return items

    def get(self, mixed, key='ID'):
        search = mixed if isinstance(mixed, list) else [mixed]
        items = []
        try:
            results = self._retrieve(search, key)
            for d in results:
                items.append(self._getStructure(d))
            items = self._applyUserData(items)
        except (Exception) as e:
            logger.logError('Exception: %s for data %s' % (str(e), repr(mixed)))
            pass

        return items
        
    def set(self, mixed):
        data = mixed if isinstance(mixed, list) else [mixed]
        try:            
            return self._replace(data)
        except (Exception) as e:
            logger.logError('Exception: %s for data %s' % (str(e), repr(mixed)))
            return False
        
    def update(self, mixed):
        data = mixed if isinstance(mixed, list) else [mixed]
        try:            
            return self._save(data)
        except (Exception) as e:
            logger.logError('Exception: %s for data %s' % (str(e), repr(mixed)))
            return False

    def delete(self, mixed):
        search = mixed if isinstance(mixed, list) else [mixed]
        try:
            return self._remove(search)
        except:
            return False
            
    def drop(self):
        try:
            return self._drop()
        except:
            return False

    def execute(self, mixed):
        queries = mixed if isinstance(mixed, list) else [mixed]
        results = []
        try: 
            dbcur = self.getCursor()
            for query in queries:
                dbcur.execute(logger.logDebug(query))
                results.append(dbcur.fetchall())
            return results
        except: 
            return False 

    def executeUpdate(self, mixed):
        queries = mixed if isinstance(mixed, list) else [mixed]
        try: 
            dbcur = self.getCursor()
            for query in queries:
                dbcur.execute(logger.logDebug(query))
            return self._dbcon.commit()
        except: 
            return False 


