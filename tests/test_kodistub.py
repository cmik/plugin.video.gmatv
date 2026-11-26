# -*- coding: utf-8 -*-
"""Stand-ins for the Kodi modules used to refresh the catalog seed outside Kodi (.github/scripts/kodistub.py)"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class KodiStubTest(unittest.TestCase):

    def test_settings_strings_and_profile(self):
        # in a separate interpreter: the stand-ins replace modules that the other tests replace too
        profile = os.path.join(tempfile.mkdtemp(), 'profile')
        script = textwrap.dedent('''
            import sys
            sys.path.insert(0, %r)
            import kodistub
            kodistub.install(%r, %r, {'cacheActive': 'false'})
            from resources.lib.libraries import control
            assert control.setting('cacheActive') == 'false', control.setting('cacheActive')
            assert control.setting('itemsPerPage') == '16', control.setting('itemsPerPage')
            assert control.lang(30215) == 'My Shows', control.lang(30215)
            assert control.dataPath == %r, control.dataPath
            assert control.addonInfo('id') == 'plugin.video.gmatv'
            control.showNotification('message')
            control.dialog.ok('title', 'message')
            print('ok')
        ''') % (os.path.join(ROOT, '.github', 'scripts'), ROOT, profile, profile)
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), 'ok', result.stderr)
        self.assertTrue(os.path.isdir(profile))

    def test_refresh_script_loads(self):
        spec = importlib.util.spec_from_file_location('refresh_catalog', os.path.join(ROOT, '.github', 'scripts', 'refresh_catalog.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.NOTHING_NEW, 3)


if __name__ == '__main__':
    unittest.main()
