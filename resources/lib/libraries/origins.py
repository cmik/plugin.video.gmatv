# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik

    The shows of GMA Play come from several catalogs (the "origin" of a show): the regular shows ('ent'),
    the movies ('fulleps') and the public affairs shows ('pa'). The last two have their own ids (an id of the
    movies can be the id of a show), services and image folder, see config.catalogs. To store everything in
    the same databases, the ids of their shows and of their episodes are shifted by an offset per catalog.
'''

import sqlite3

from resources import config

# the catalog of the regular shows has no offset and no specific service
ENT = ''


def originOfShow(show):
    """The catalog ('fulleps', 'pa'...) of a show of the website (a dict of a shelf), '' for a regular show"""
    origin = show.get('origin')
    return origin if origin in config.catalogs else ENT


def originOfId(itemId):
    """The catalog of an id (of a show or of an episode) as stored in the databases"""
    try:
        itemId = int(itemId)
    except (TypeError, ValueError):
        return ENT
    for origin, catalog in sorted(config.catalogs.items(), key=lambda c: c[1]['offset'], reverse=True):
        if itemId >= catalog['offset']:
            return origin
    return ENT


def toStoredId(origin, apiId):
    """The id stored in the databases for an id of the website"""
    return int(apiId) + (config.catalogs[origin]['offset'] if origin else 0)


def toApiId(itemId):
    """The id to give to the website services"""
    origin = originOfId(itemId)
    return int(itemId) - (config.catalogs[origin]['offset'] if origin else 0)


def service(origin, name, default):
    """The service `name` ('details', 'nbPages', 'episodes') of a catalog, the regular one (`default`) for a show"""
    return config.catalogs[origin][name] if origin else default


def imageSection(origin):
    """The folder of the images of a catalog on the CDN"""
    return config.catalogs[origin]['imageSection'] if origin else 'entertainment'


def ltype(origin, nbEpisodes):
    """'movie' only for a title of the movies catalog with a single episode: that catalog also holds series
    (several episodes), which are listed like the other shows"""
    return 'movie' if origin == 'fulleps' and nbEpisodes == 1 else 'show'


def fixTypes(showsPath, episodesPath):
    """Give the type 'show' to the titles of the movies catalog stored as movies by the first catalog reloads
    although they have several episodes (and to their episodes). Returns the number of shows changed."""
    changed = 0
    try:
        con = sqlite3.connect(showsPath)
        try:
            con.execute('ATTACH ? AS e', (episodesPath,))
            first = config.catalogs['fulleps']['offset']
            last = config.catalogs['pa']['offset']
            several = 'SELECT SHOWID FROM e.EPISODE WHERE SHOWID >= ? AND SHOWID < ? GROUP BY SHOWID HAVING COUNT(*) > 1'
            con.execute("UPDATE e.EPISODE SET TYPE = 'show' WHERE TYPE = 'movie' AND SHOWID IN (%s)" % several, (first, last))
            changed = con.execute("UPDATE SHOW SET TYPE = 'show' WHERE TYPE = 'movie' AND ID IN (%s)" % several, (first, last)).rowcount
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        # no table yet (new installation): nothing to fix
        return 0
    return changed
