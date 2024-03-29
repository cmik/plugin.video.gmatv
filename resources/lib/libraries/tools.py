# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

import os,xbmcvfs
from resources import config
from resources.lib.libraries import control

logger = control.logger

def importShowDB():
    fileSource = logger.logInfo(control.browse(1, 'Select your shows DB file', 'files', '.db'))
    if (fileSource != ''):
        logger.logInfo(xbmcvfs.copy(fileSource, control.showsFile))
        control.showNotification(control.lang(37040), control.lang(30010))

def importEpisodeDB():
    fileSource = logger.logInfo(control.browse(1, 'Select your episodes DB file', 'files', '.db'))
    if (fileSource != ''):
        logger.logInfo(xbmcvfs.copy(fileSource, control.episodesFile))
        control.showNotification(control.lang(37040), control.lang(30010))

def importDBFiles():
    status = True
    try:
        dBImportURL = control.setting('databaseImportURL')
        
        # Shows DB file
        fileSource = dBImportURL + 'shows.db' 
        logger.logInfo('Copying %s to %s' % (fileSource, control.showsFile))
        status = True if status is True and logger.logInfo(xbmcvfs.copy(fileSource, control.showsFile)) != 0 else False

        # Episodes DB file
        fileSource = dBImportURL + 'episodes.db' 
        logger.logInfo('Copying %s to %s' % (fileSource, control.episodesFile))
        status = True if status is True and logger.logInfo(xbmcvfs.copy(fileSource, control.episodesFile)) != 0 else False

        # Celebrities DB file
        fileSource = dBImportURL + 'celebrities.db' 
        logger.logInfo('Copying %s to %s' % (fileSource, control.celebritiesFile))
        status = True if status is True and logger.logInfo(xbmcvfs.copy(fileSource, control.celebritiesFile)) != 0 else False
    except:
        status = False
        pass
    if status is True:
        control.setSetting('showUpdateCatalog', 'false')
        control.showNotification(control.lang(37003), control.lang(30010))
    else:
        control.showNotification(control.lang(37027), control.lang(30004))
    return status

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
    control.showNotification(control.lang(30005))
    isInstalled = isDBInstalled()
    
    if refresh == True and isInstalled == True:
        deleteDBFiles()
    
    if refresh == True or isInstalled == False:
        # control.run(config.IMPORTALLDB, 'install')
        importDBFiles()

def isDBInstalled():
    if control.setting('showUpdateCatalog') == 'false' and os.path.exists(control.episodesFile) and os.path.exists(control.showsFile):
        return True
    return False
