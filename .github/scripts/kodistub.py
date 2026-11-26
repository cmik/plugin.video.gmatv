"""Stand-ins for the Kodi modules (xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs), so that the add-on code
can run outside Kodi (refresh_catalog.py). Only what the catalog code needs does something: the settings
(defaults of resources/settings.xml, then the given overrides), the strings of the language file, the
add-on profile folder and the log (printed). Everything else (dialogs, listings...) does nothing.

    import kodistub
    kodistub.install(root, profile, settings={'cacheActive': 'false'})
"""

import os
import re
import sys
import types
import xml.etree.ElementTree as ET


class _Anything(object):
    """Any attribute, call or item: does nothing and returns another _Anything (or the default values below)"""

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _Anything()

    def __getattr__(self, name):
        return _Anything()

    def __bool__(self):
        return False

    def __iter__(self):
        return iter(())

    def __str__(self):
        return ''


def _settings(root):
    values = {}
    for node in ET.parse(os.path.join(root, 'resources', 'settings.xml')).iter('setting'):
        if node.get('id'):
            values[node.get('id')] = node.get('default', '')
    return values


def _strings(root):
    strings = {}
    path = os.path.join(root, 'resources', 'language', 'resource.language.en_gb', 'strings.po')
    with open(path, encoding='utf-8') as f:
        for number, text in re.findall(r'msgctxt "#(\d+)"\s*\nmsgid "((?:[^"\\]|\\.)*)"', f.read()):
            strings[int(number)] = text.replace('\\"', '"')
    return strings


def install(root, profile, settings=None, verbose=False):
    os.makedirs(profile, exist_ok=True)
    values = _settings(root)
    values.update(settings or {})
    strings = _strings(root)
    addonXml = ET.parse(os.path.join(root, 'addon.xml')).getroot()
    info = {'id': addonXml.get('id'), 'name': addonXml.get('name'), 'version': addonXml.get('version'),
            'path': root, 'profile': profile, 'icon': '', 'fanart': ''}

    xbmc = types.ModuleType('xbmc')
    for i, level in enumerate(('LOGDEBUG', 'LOGINFO', 'LOGNOTICE', 'LOGWARNING', 'LOGERROR', 'LOGSEVERE', 'LOGFATAL', 'LOGNONE')):
        setattr(xbmc, level, i)
    xbmc.PLAYLIST_VIDEO = 1

    def log(message, level=1):
        if verbose or level >= xbmc.LOGWARNING:
            print(message, file=sys.stderr)
    xbmc.log = log
    xbmc.getInfoLabel = lambda label: ''
    xbmc.getCondVisibility = lambda condition: False
    xbmc.getSkinDir = lambda: ''
    xbmc.executebuiltin = lambda *args, **kwargs: None
    xbmc.executeJSONRPC = lambda request: '{}'
    xbmc.sleep = lambda ms: None
    for name in ('Keyboard', 'Player', 'PlayList', 'Monitor'):
        setattr(xbmc, name, _Anything)

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, id=None):
            pass

        def getSetting(self, key):
            return values.get(key, '')

        def setSetting(self, key, value):
            values[key] = value

        def getLocalizedString(self, number):
            return strings.get(int(number), '')

        def getAddonInfo(self, key):
            return info.get(key, '')
    xbmcaddon.Addon = Addon

    xbmcgui = types.ModuleType('xbmcgui')
    for name in ('ListItem', 'Window', 'Dialog', 'DialogProgress', 'DialogProgressBG', 'WindowDialog', 'ControlButton', 'ControlImage'):
        setattr(xbmcgui, name, _Anything)
    xbmcgui.NOTIFICATION_INFO = 'info'

    xbmcplugin = types.ModuleType('xbmcplugin')
    for name in ('addDirectoryItem', 'addDirectoryItems', 'endOfDirectory', 'setContent', 'addSortMethod', 'setProperty', 'setResolvedUrl'):
        setattr(xbmcplugin, name, lambda *args, **kwargs: None)

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda path: path
    xbmcvfs.exists = os.path.exists
    xbmcvfs.mkdir = lambda path: os.makedirs(path, exist_ok=True) or True
    xbmcvfs.mkdirs = xbmcvfs.mkdir
    xbmcvfs.delete = lambda path: os.remove(path) if os.path.exists(path) else None
    xbmcvfs.rmdir = lambda path: os.rmdir(path) if os.path.isdir(path) else None
    xbmcvfs.listdir = lambda path: ([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))],
                                    [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    xbmcvfs.File = open

    for module in (xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs):
        sys.modules[module.__name__] = module
    if root not in sys.path:
        sys.path.insert(0, root)
    return values
