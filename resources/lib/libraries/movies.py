# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik

    The movies of GMA Play (origin 'fulleps') are a separate catalog: their ids are not the ids of the shows
    (2473 is both a show and a movie) and neither are the ids of their episodes. To store both in the same
    databases, the ids of the movies and of their episodes are shifted by an offset; the website services
    are called with the real id.
'''

import sqlite3

from resources import config

# origin of the shows that are movies
ORIGIN = 'fulleps'

# folder of the images of the movies on the CDN
IMAGE_SECTION = 'fulleps'


def isMovie(show):
    """True for a show of the website (a dict of a shelf) that is a movie"""
    return show.get('origin') == ORIGIN


def isMovieId(itemId):
    """True for an id (of a show or of an episode) of the movies"""
    try:
        return int(itemId) >= config.movieIdOffset
    except (TypeError, ValueError):
        return False


def toMovieId(apiId):
    """The id stored in the databases for an id of the website"""
    return int(apiId) + config.movieIdOffset


def toApiId(itemId):
    """The id to give to the website services"""
    return int(itemId) - config.movieIdOffset if isMovieId(itemId) else int(itemId)


def ltype(isMovie, nbEpisodes):
    """'movie' only for a movie with a single episode: the catalog of the movies also holds series
    (several episodes), which are listed like the other shows"""
    return 'movie' if isMovie and nbEpisodes == 1 else 'show'


def fixTypes(showsPath, episodesPath):
    """Give the type 'show' to the titles of the movies catalog stored as movies by the first catalog reloads
    although they have several episodes (and to their episodes). Returns the number of shows changed."""
    changed = 0
    try:
        con = sqlite3.connect(showsPath)
        try:
            con.execute('ATTACH ? AS e', (episodesPath,))
            several = 'SELECT SHOWID FROM e.EPISODE WHERE SHOWID >= ? GROUP BY SHOWID HAVING COUNT(*) > 1'
            offset = config.movieIdOffset
            con.execute("UPDATE e.EPISODE SET TYPE = 'show' WHERE TYPE = 'movie' AND SHOWID IN (%s)" % several, (offset,))
            changed = con.execute("UPDATE SHOW SET TYPE = 'show' WHERE ID >= ? AND TYPE = 'movie' AND ID IN (%s)" % several, (offset, offset)).rowcount
            con.commit()
        finally:
            con.close()
    except sqlite3.Error:
        # no table yet (new installation): nothing to fix
        return 0
    return changed
