# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik

    Background service: runs the periodic tasks of the add-on (see service.py).
'''

import time
import xbmc
from resources import config
from resources.lib.libraries import control

# first run of the tasks this long after Kodi starts, so the start isn't slowed down
START_DELAY = 60


def scheduledTasks():
    """The (name, mode, interval in seconds) of the tasks to run, read once at start (restart Kodi after a change)"""
    tasks = []
    if control.setting('exportToLibrary') == 'true' and control.setting('libraryAutoUpdate') == 'true':
        try:
            minutes = int(control.setting('librayCheckSchedule'))
        except ValueError:
            minutes = 60
        tasks.append(('library checker', config.CHECKLIBRARYUPDATES, 60 * max(minutes, 5)))
    return tasks


def run():
    name = control.addonInfo('name')
    tasks = scheduledTasks()
    if not tasks:
        xbmc.log('[%s] Service: nothing to schedule' % name, level=xbmc.LOGINFO)
        return
    for (task, mode, interval) in tasks:
        xbmc.log('[%s] Service: %s every %d minutes' % (name, task, interval // 60), level=xbmc.LOGINFO)

    monitor = xbmc.Monitor()
    nextRuns = dict((mode, time.time() + START_DELAY) for (task, mode, interval) in tasks)
    while not monitor.abortRequested():
        now = time.time()
        for (task, mode, interval) in tasks:
            if now >= nextRuns[mode]:
                nextRuns[mode] = now + interval
                control.run(mode, 'service')
        # wake up at the next run, or every 10 s to stop quickly when Kodi exits
        if monitor.waitForAbort(max(1, min(10, min(nextRuns.values()) - time.time()))):
            break
    xbmc.log('[%s] Service: stopped' % name, level=xbmc.LOGINFO)
