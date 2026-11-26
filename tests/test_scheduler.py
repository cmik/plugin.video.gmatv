# -*- coding: utf-8 -*-
"""Background service: which tasks are scheduled and when they run"""

import sys
import types
import unittest
from unittest import mock

import test_userdata  # noqa: F401 (replaces the Kodi modules)
from resources.lib.libraries import control

# the scheduler needs xbmc (log and Monitor) and the mode constants: give it stand-ins
if 'xbmc' not in sys.modules:
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO = 1
    xbmc.log = lambda *args, **kwargs: None
    xbmc.Monitor = object
    sys.modules['xbmc'] = xbmc
if 'resources.config' not in sys.modules:
    config = types.ModuleType('resources.config')
    config.CHECKLIBRARYUPDATES = 26
    sys.modules['resources.config'] = config
    import resources
    resources.config = config

from resources.lib.services import scheduler  # noqa: E402


class FakeMonitor(object):
    """Lets the clock go forward by the waited time, and asks to stop after `rounds` waits"""

    def __init__(self, clock, rounds):
        self.clock = clock
        self.rounds = rounds

    def abortRequested(self):
        return self.rounds <= 0

    def waitForAbort(self, seconds):
        self.clock[0] += seconds
        self.rounds -= 1
        return self.rounds <= 0


def settings(values):
    return lambda key: values.get(key, '')


class SchedulerTest(unittest.TestCase):

    def setUp(self):
        control.addonInfo = lambda key: 'GMA.tv'

    def tasks(self, values):
        with mock.patch.object(control, 'setting', settings(values), create=True):
            return scheduler.scheduledTasks()

    def test_library_checker_only_when_export_and_auto_update_are_on(self):
        self.assertEqual(self.tasks({}), [])
        self.assertEqual(self.tasks({'libraryAutoUpdate': 'true'}), [])
        self.assertEqual(self.tasks({'exportToLibrary': 'true', 'libraryAutoUpdate': 'true', 'librayCheckSchedule': '30'}),
                         [('library checker', 26, 1800)])

    def test_bad_or_too_short_schedule(self):
        on = {'exportToLibrary': 'true', 'libraryAutoUpdate': 'true'}
        self.assertEqual(self.tasks(dict(on, librayCheckSchedule='abc'))[0][2], 3600)
        self.assertEqual(self.tasks(dict(on, librayCheckSchedule='1'))[0][2], 300)

    def test_runs_after_the_start_delay_then_at_each_interval(self):
        clock = [1000.0]
        runs = []
        values = {'exportToLibrary': 'true', 'libraryAutoUpdate': 'true', 'librayCheckSchedule': '5'}
        with mock.patch.object(control, 'setting', settings(values), create=True), \
                mock.patch.object(control, 'run', lambda mode, caller: runs.append((clock[0], mode, caller)), create=True), \
                mock.patch.object(scheduler.time, 'time', lambda: clock[0]), \
                mock.patch.object(scheduler.xbmc, 'Monitor', lambda: FakeMonitor(clock, 100)):
            scheduler.run()
        # 60 s after the start, then every 5 minutes, and never in a busy loop
        self.assertEqual([r[0] for r in runs[:3]], [1060.0, 1360.0, 1660.0])
        self.assertTrue(all(r[1:] == (26, 'service') for r in runs))

    def test_nothing_to_schedule_returns_at_once(self):
        with mock.patch.object(control, 'setting', settings({}), create=True), \
                mock.patch.object(scheduler.xbmc, 'Monitor', side_effect=AssertionError('no loop expected')):
            scheduler.run()


if __name__ == '__main__':
    unittest.main()
