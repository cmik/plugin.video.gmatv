# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik

    The movies of GMA Play (origin 'fulleps') are a separate catalog: their ids are not the ids of the shows
    (2473 is both a show and a movie) and neither are the ids of their episodes. To store both in the same
    databases, the ids of the movies and of their episodes are shifted by an offset; the website services
    are called with the real id.
'''

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
