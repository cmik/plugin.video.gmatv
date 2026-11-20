# -*- coding: utf-8 -*-
"""The execution cache and its StorageServer stand-in: python -m unittest discover -s tests"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# these two modules don't need Kodi: load them from their files (the package __init__ files import nothing)
import importlib.util  # noqa: E402


def load(name, relativePath):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relativePath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


executioncache = load('executioncache', 'resources/lib/libraries/executioncache.py')
storageserverdummy = load('storageserverdummy', 'resources/lib/dummy/storageserverdummy.py')


class CacheTest(unittest.TestCase):

    def test_clean_forgets_everything_when_forced(self):
        shared = {}
        cache = executioncache.ExecutionCache(shared)
        cache.set('a', 1)
        cache.setMulti('k', {'url': 'x', 'timestamp': 2})
        self.assertEqual(1, cache.get('a'))
        self.assertTrue(cache.cacheClean())  # not forced: nothing to expire in an execution cache
        self.assertEqual(1, cache.get('a'))
        self.assertTrue(cache.cacheClean(True))
        self.assertEqual(['', ''], [cache.get('a'), cache.get('kurl')])
        self.assertEqual({}, shared)

    def test_the_stand_in_has_the_same_methods(self):
        server = storageserverdummy.StorageServer('t', 1)
        for name in ('cacheFunction', 'set', 'get', 'setMulti', 'getMulti', 'lock', 'unlock', 'cacheClean'):
            self.assertTrue(hasattr(server, name), name)
            self.assertTrue(hasattr(executioncache.ExecutionCache({}), name), name)
        self.assertTrue(server.cacheClean(True))


if __name__ == '__main__':
    unittest.main()
