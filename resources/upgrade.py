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

    if control.setting('lastVersion') in (''):
        # Check if installation is complete
        logger.logNotice('Checking installation')
        tools.checkInstallDB(True)

    tools.checkInstallDB()

    # the first catalog reloads stored as movies the titles of the movies catalog that have several episodes
    from resources.lib.libraries import movies
    logger.logNotice('Movie types fixed: %d' % movies.fixTypes(control.showsFile, control.episodesFile))

def upgradeSettings():
    return True