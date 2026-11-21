# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

import os,xbmcvfs
from resources import config
from resources.lib.libraries import control

logger = control.logger

def importUserData():
    """Move the counters stored in the catalog databases by the previous versions to the user data database (done once)"""
    try:
        from resources.lib.models import userdata
        return userdata.UserData(control.userDataFile).importLegacy(control.showsFile, control.episodesFile)
    except Exception as e:
        logger.logError('Can\'t import the user data: %s' % str(e))
        return 0

def importDBFiles():
    """Install the catalog seed (ready-made shows, episodes and celebrities databases), then look for
    what is new since it was built, in the background. Returns True when it was installed."""
    from resources.lib.libraries import seed
    control.showNotification(control.lang(37051), control.lang(30005))
    importUserData()  # before the catalog databases are replaced
    manifest = seed.installCatalogSeed(
        control.setting('catalogSeedURL'),
        {'shows.db': control.showsFile, 'episodes.db': control.episodesFile, 'celebrities.db': control.celebritiesFile},
        lambda percent: control.showNotification('%d%%' % percent, control.lang(37051), time=1000) if percent % 25 == 0 else None
    )
    if manifest is None:
        control.showNotification(control.lang(37053), control.lang(30004), time=8000)
        return False
    control.setSetting('showUpdateCatalog', 'false')
    control.setSetting('catalogSeedVersion', manifest.get('catalogVersion', ''))
    control.showNotification(control.lang(37052), control.lang(30010))
    # the shows that are new since the seed was built
    control.execute('RunPlugin(plugin://%s/?mode=%d&caller=seed)' % (control.addonInfo('id'), config.CATCHUPCATALOG))
    return True

def deleteDBFiles():
    status = True
    try:
        if control.pathExists(control.showsFile):
            logger.logInfo('Deleting %s' % control.showsFile)
            status = True if status is True and logger.logInfo(xbmcvfs.delete(control.showsFile)) != 0 else False

        if control.pathExists(control.episodesFile):
            logger.logInfo('Deleting %s' % control.episodesFile)
            status = True if status is True and logger.logInfo(xbmcvfs.delete(control.episodesFile)) != 0 else False

        if control.pathExists(control.celebritiesFile):
            logger.logInfo('Deleting %s' % control.celebritiesFile)
            status = True if status is True and logger.logInfo(xbmcvfs.delete(control.celebritiesFile)) != 0 else False
    except:
        status = False
        pass
    return status

def checkInstallDB(refresh=False):
    """Install the catalog seed when asked (refresh) or when there is no catalog yet. The databases
    in place are replaced only once the seed has been downloaded and checked."""
    control.showNotification(control.lang(30005))
    if refresh == True or isDBInstalled() == False:
        importDBFiles()

def isDBInstalled():
    if control.setting('showUpdateCatalog') == 'false' and os.path.exists(control.episodesFile) and os.path.exists(control.showsFile):
        return True
    return False
