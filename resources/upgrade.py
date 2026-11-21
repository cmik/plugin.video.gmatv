# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import tools
from resources.lib.models import episodes
from resources.lib.models import shows
from resources.lib.models import library

logger = control.logger

def upgradeDB():

    logger.logNotice('Updating from version %s to %s' % (control.setting('lastVersion'), control.addonInfo('version')))

    # the counters stored in the catalog databases must leave them before anything replaces them
    tools.importUserData()

    # first installation or update from 1.x (other catalog ids): install the ready-made catalog
    from resources.lib.libraries import seed
    reason = seed.seedReason(control.setting('lastVersion'))
    if reason:
        logger.logNotice('Installing the catalog seed (%s)' % reason)
        tools.checkInstallDB(True)
    else:
        tools.checkInstallDB()

    # the first catalog reloads stored as movies the titles of the movies catalog that have several episodes
    from resources.lib.libraries import origins
    logger.logNotice('Movie types fixed: %d' % origins.fixTypes(control.showsFile, control.episodesFile))

    # image URLs without an image name (HTTP 404 in Kodi), stored before the empty names were handled
    from resources.lib.libraries import dbfixes
    for path, table in ((control.showsFile, 'SHOW'), (control.episodesFile, 'EPISODE'), (control.celebritiesFile, 'SHOW_CAST')):
        logger.logNotice('Empty images fixed in %s: %d' % (table, dbfixes.fixEmptyImages(path, table)))

def upgradeSettings():
    return True