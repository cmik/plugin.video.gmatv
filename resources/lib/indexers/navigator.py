# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import os,sys,xbmc,time,re
from urllib.parse import parse_qsl,quote_plus,urlencode
from resources import config
from resources.lib.libraries import control
from resources.lib.libraries import cache
from resources.lib.sources import gmatv
from operator import itemgetter

artPath = control.artPath()
addonFanart = control.addonFanart()
logger = control.logger

try: 
    action = dict(parse_qsl(sys.argv[2].replace('?','')))['action']
except:
    action = None

sysaddon = sys.argv[0]
thisPlugin = int(sys.argv[1])

class navigator:

    def root(self):            
        self.showMainMenu()
    
    def showMainMenu(self):
        self.addDirectoryItem(control.lang(30204), '/', config.SEARCHMENU, control.addonFolderIcon(control.lang(30204)), isFolder=True, **self.formatMenu())

        # if control.setting('displayMyList') == 'true':
        #     self.addDirectoryItem(control.lang(30200), '/', config.MYLIST, control.addonFolderIcon(control.lang(30200)), isFolder=True, **self.formatMenu())
        
        # if control.setting('displayWebsiteSections') == 'true':
        #     self.addDirectoryItem(control.lang(30201), '/', config.CATEGORIES, control.addonFolderIcon(control.lang(30201)), isFolder=True, **self.formatMenu())
        # else:
        #     self.showCategories()
        if control.setting('displayWebsiteSections') == 'true':
            control.showNotification(control.lang(37020), control.lang(30008))
            sections = gmatv.getWebsiteHomeSections()
            for s in sections:
                self.addDirectoryItem(s['name'].title(), str(s['id']), config.SECTIONCONTENT, control.addonFolderIcon(s['name'].title()), isFolder=True, **self.formatMenu())
            
        if control.setting('exportToLibrary') == 'true':
            self.addDirectoryItem(control.lang(36023), '/', config.EXPORTEDSHOWS, control.addonFolderIcon(control.lang(36023)), isFolder=True, **self.formatMenu())
        
        if control.setting('displayTools') == 'true':
            self.addDirectoryItem(control.lang(30203), '/', config.TOOLS, control.addonFolderIcon(control.lang(30203)))
            
        self.endDirectory()
            
    def showMyList(self):   
        self.addDirectoryItem(control.lang(30213), '/', config.MYLISTSHOWLASTEPISODES, control.addonFolderIcon(control.lang(30213)), isFolder=True, **self.formatMenu())
        categories = gmatv.getMyListCategories()
        for c in categories:
            self.addDirectoryItem(c.get('name'), str(c.get('id')), config.LISTCATEGORY, control.addonFolderIcon(c.get('name')), **self.formatMenu())
        self.endDirectory()

    def showMyListShowLastEpisodes(self):   
        episodes = gmatv.getMylistShowLastEpisodes()
        for e in episodes:
            title = '%s - %s' % (e.get('show'), e.get('dateaired'))
            self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query='title=%s' % title, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory()

    def showMyListCategory(self, url):   
        items = gmatv.getMylistCategoryItems(url)
        for e in items:
            if e['type'] == 'show':
                image = e.get('logo') if control.setting('useShowLogo') == 'true' else e.get('image')
                self.addDirectoryItem(e.get('name'), str(e.get('id')), config.SHOWEPISODES, image, isFolder=True, query='parentid='+str(e.get('parentid'))+'&year='+e.get('year'), **self.formatShowInfo(e, addToList=False))
            elif e['type'] == 'episode':
                title = '%s - %s' % (e.get('show'), e.get('dateaired')) # if e.get('type') == 'movie' else '%s - Ep.%s - %s' % (e.get('show'), e.get('episodenumber'), e.get('dateaired'))
                self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query='title=%s' % title, **self.formatVideoInfo(e, addToList=False))
        self.endDirectory()
            
    def showCategories(self):
        categories = gmatv.getCategories()
        for c in categories:
            self.addDirectoryItem(c.get('name'), str(c.get('id')), config.SUBCATEGORIES, control.addonFolderIcon(c.get('name')), isFolder=True, **self.formatMenu())
            
        if control.setting('displayWebsiteSections') == 'true':
            self.endDirectory()
          
    def showSubCategories(self, categoryId):
        subCategories = gmatv.getSubCategories(categoryId)
        for s in subCategories:
            self.addDirectoryItem(s.get('name'), str(s.get('id')), config.SUBCATEGORYSHOWS, control.addonFolderIcon(s.get('name')), isFolder=True, **self.formatMenu())
        self.endDirectory()
       
    def showSubCategoryShows(self, subCategoryId):
        shows = gmatv.getShows(subCategoryId)
        if len(shows) > 0:
            self.displayShows(shows)
        else:
            self.endDirectory()
        
    def showWebsiteSectionContent(self, section, page=1):
        itemsPerPage = int(control.setting('itemsPerPage'))
        content = gmatv.getWebsiteSectionContent(section, page, itemsPerPage)
        for e in content:
            if e['type'] == 'show':
                image = e.get('logo') if control.setting('useShowLogo') == 'true' else e.get('image')
                self.addDirectoryItem(e.get('name'), str(e.get('id')), config.SHOWEPISODES, image, isFolder=True, **self.formatShowInfo(e))
            elif e['type'] == 'episode':
                title = '%s - %s' % (e.get('show'), e.get('dateaired')) # if e.get('type') == 'movie' else '%s - Ep.%s - %s' % (e.get('show'), e.get('episodenumber'), e.get('dateaired'))
                self.addDirectoryItem(title, str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query='title=%s' % title, **self.formatVideoInfo(e))
        if len(content) == itemsPerPage:
            self.addDirectoryItem(control.lang(36008), section, config.SECTIONCONTENT, '', page + 1)
        self.endDirectory()

    def displayShows(self, shows):
        sortedShowInfos = []
        for show in shows:
            image = show['logo'] if control.setting('useShowLogo') == 'true' else show['image']
            sortedShowInfos.append((show.get('name').lower(), show.get('name'), str(show.get('id')), config.SHOWEPISODES, image, 'parentid='+str(show.get('parentid'))+'&year='+show.get('year'), self.formatShowInfo(show)))
        
        sortedShowInfos = sorted(sortedShowInfos, key = itemgetter(0))
        for info in sortedShowInfos:
            self.addDirectoryItem(info[1], info[2], info[3], info[4], isFolder=True, query=info[5], **info[6])
                
        self.endDirectory()
        
    def showEpisodes(self, showId, page=1, parentId=-1, year=''):
        itemsPerPage = int(control.setting('itemsPerPage'))
        (episodes, nextPage) = gmatv.getEpisodesPerPage(showId, parentId, year, page, itemsPerPage)
        episodes = sorted(episodes, key=lambda item: item['episodenumber'], reverse=True)
        for e in episodes:
            self.addDirectoryItem(e.get('title'), str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query='title=%s' % e.get('title'), **self.formatVideoInfo(e))
        if len(episodes) == itemsPerPage or nextPage == True:
            self.addDirectoryItem(control.lang(36008), showId, config.SHOWEPISODES, '', page + 1)
        self.endDirectory()

    def showSearchMenu(self, category):    
        if category == 'movieshow':
            self.addDirectoryItem(control.lang(30208), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30209), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30209)), isFolder=True, query='category=%s&type=%s' % (category, 'category'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30210), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30210)), isFolder=True, query='category=%s&type=%s' % (category, 'cast'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30212), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30212)), isFolder=True, query='category=%s&type=%s' % (category, 'year'), **self.formatMenu())
        elif category == 'episode':
            self.addDirectoryItem(control.lang(30208), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30208)), isFolder=True, query='category=%s&type=%s' % (category, 'title'), **self.formatMenu())
            self.addDirectoryItem(control.lang(30211), '/', config.EXECUTESEARCH, control.addonFolderIcon(control.lang(30211)), isFolder=True, query='category=%s&type=%s' % (category, 'date'), **self.formatMenu())
        elif category == 'celebrity':
            control.showNotification(control.lang(37026), control.lang(30001))
        else:
             self.addDirectoryItem(control.lang(30205), '/', config.SEARCHMENU, control.addonFolderIcon(control.lang(30205)), isFolder=True, query='category=%s' % 'movieshow', **self.formatMenu())
             self.addDirectoryItem(control.lang(30206), '/', config.SEARCHMENU, control.addonFolderIcon(control.lang(30206)), isFolder=True, query='category=%s' % 'episode', **self.formatMenu())
             self.addDirectoryItem(control.lang(30207), '/', config.SEARCHMENU, control.addonFolderIcon(control.lang(30207)), isFolder=True, query='category=%s' % 'celebrity', **self.formatMenu())
        self.endDirectory()

    def executeSearch(self, category, type):
        if category != False and type != False:
            result = gmatv.enterSearch(category, type)
            if len(result) > 0:
                if category == 'movieshow':
                    self.displayShows(result)
                    return True
                elif category == 'episode':
                    for e in result:
                        self.addDirectoryItem(e.get('title'), str(e.get('id')), config.PLAY, e.get('image'), isFolder = False, query='title=%s' % e.get('title'), **self.formatVideoInfo(e))
        self.endDirectory()
            
    def showMyAccount(self):
        gmatv.checkAccountChange(False)
        categories = [
            { 'name' : control.lang(36004), 'url' : config.uri.get('profile'), 'mode' : config.MYINFO },
            { 'name' : control.lang(36005), 'url' : config.uri.get('base'), 'mode' : config.MYSUBSCRIPTIONS },
            { 'name' : control.lang(36006), 'url' : config.uri.get('base'), 'mode' : config.MYTRANSACTIONS }
        ]
        for c in categories:
            self.addDirectoryItem(c.get('name'), c.get('url'), c.get('mode'), control.addonFolderIcon(c.get('name')))
        self.addDirectoryItem(control.lang(36007), config.uri.get('base'), config.LOGOUT, control.addonFolderIcon('Logout'), isFolder = False)    
        self.endDirectory()
    
    def showMyInfo(self):
        loggedIn = gmatv.isLoggedIn()
        message = control.lang(37002)
        if loggedIn == True:
            try:
                user = gmatv.getUserInfo()
                message = 'First name: %s\nLast name: %s\nEmail: %s\nState: %s\nCountry: %s\nMember since: %s\n\n' % (
                    user.get('firstName', ''),
                    user.get('lastName', ''), 
                    user.get('email', ''), 
                    user.get('state', ''),
                    user.get('country', ''), 
                    user.get('memberSince', '')
                    )
            except:
                pass
        control.showMessage(message, control.lang(36001))
    
    def showMySubscription(self):
        sub = gmatv.getUserSubscription()
        message = ''
        if sub:
            message += '%s' % (sub.get('details'))
        else:
            message = control.lang(37002)
        control.showMessage(message, control.lang(36002))
        
    def showMyTransactions(self):
        transactions = gmatv.getUserTransactions()
        message = ''
        if len(transactions) > 0:
            for t in transactions:
                message += t + "\n"
        else:
            message = control.lang(37002)
        control.showMessage(message, control.lang(36003))

    def showExportedShows(self):
        exported = gmatv.showExportedShowsToLibrary()
        self.displayShows(exported)

    def removeShowFromLibrary(self, id, name):
        gmatv.removeFromLibrary(id, name)
        control.refresh()
            
    def showTools(self):
        self.addDirectoryItem(control.lang(36021), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(36021)))
        self.addDirectoryItem(control.lang(36019), config.uri.get('base'), config.IMPORTSHOWDB, control.addonFolderIcon(control.lang(36019)))
        self.addDirectoryItem(control.lang(36020), config.uri.get('base'), config.IMPORTEPISODEDB, control.addonFolderIcon(control.lang(36020)))
        self.addDirectoryItem(control.lang(36009), config.uri.get('base'), config.RELOADCATALOG, control.addonFolderIcon(control.lang(36009)))
        self.addDirectoryItem(control.lang(36018), config.uri.get('base'), config.RESETCATALOG, control.addonFolderIcon(control.lang(36018)))
        self.addDirectoryItem(control.lang(36017), config.uri.get('base'), config.CHECKLIBRARYUPDATES, control.addonFolderIcon(control.lang(36017)))
        self.addDirectoryItem(control.lang(36010), config.uri.get('base'), config.CLEANCOOKIES, control.addonFolderIcon(control.lang(36010)))
        self.addDirectoryItem(control.lang(36022), config.uri.get('base'), config.FIRSTINSTALL, control.addonFolderIcon(control.lang(36022)))
        self.endDirectory()
            
    def firstInstall(self):
        if control.setting('showWelcomeMessage') == 'true':
            control.showMessage(control.lang(37016), control.lang(37018))
            control.setSetting('showWelcomeMessage', 'false')
        if control.setting('emailAddress') == '':
            if control.setting('showEnterCredentials') == 'true':
                self.addDirectoryItem(control.lang(36011), config.uri.get('base'), config.ENTERCREDENTIALS, control.addonFolderIcon(control.lang(36011)))
            # self.addDirectoryItem(control.lang(36012) % (' ' if control.setting('showPersonalize') == 'true' else 'x'), config.uri.get('base'), config.PERSONALIZESETTINGS, control.addonFolderIcon(control.lang(36012)))
            # self.addDirectoryItem(control.lang(36013) % (' ' if control.setting('showUpdateCatalog') == 'true' else 'x'), config.uri.get('base'), config.IMPORTALLDB, control.addonFolderIcon(control.lang(36013)))
            self.addDirectoryItem(control.lang(36014) % (control.lang(36015) if control.setting('showEnterCredentials') == 'true' else control.lang(36016)), config.uri.get('base'), config.ENDSETUP, control.addonFolderIcon('Skip'))
            self.endDirectory()
        else:
            self.endSetup()
        
    def enterCredentials(self):
        if gmatv.enterCredentials() == True:
            control.setSetting('showEnterCredentials', 'false')
            self.endSetup()
        
    def optimizeLibrary(self):
        gmatv.reloadCatalogCache()
        control.setSetting('showUpdateCatalog', 'false')
        control.refresh()
        
    def personalizeSettings(self):
        control.openSettings()
        control.setSetting('showPersonalize', 'false')
        control.refresh()
        
    def endSetup(self):
        control.setSetting('addonNewInstall', 'false')
        # control.refresh()
        self.showMainMenu()
        
    def formatMenu(self, bgImage=''):
        if bgImage == '': bgImage = control.setting('defaultBG')
        data = { 
            'listArts' : { 'fanart' : bgImage, 'banner' : bgImage }
            }
        return data
        
    def formatShowInfo(self, info, addToList=True, options = {}):
        contextMenu = {}
        # add to mylist / remove from mylist
        add = { control.lang(30300) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('name'), query='ltype=%s&type=%s' % (info.get('ltype'), info.get('type'))) } 
        remove = { control.lang(30301) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('name'), query='ltype=%s&type=%s' % (info.get('ltype'), info.get('type'))) } 
        if addToList == True: 
            contextMenu.update(add)
        else:
            contextMenu.update(remove)
        # export to library
        if control.setting('exportToLibrary') == 'true':
            addToLibrary = { control.lang(30302) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIBRARY, info.get('name'), query='parentid=%s&year=%s&ltype=%s&type=%s' % (str(info.get('parentid')), info.get('year'), info.get('ltype'), info.get('type'))) }
            removeFromLibrary = { control.lang(30304) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIBRARY, info.get('name'), query='parentid=%s&year=%s&ltype=%s&type=%s' % (str(info.get('parentid')), info.get('year'), info.get('ltype'), info.get('type'))) }
            if info.get('inLibrary', False) == True:
                contextMenu.update(removeFromLibrary)
            else:
                contextMenu.update(addToLibrary)
            
        
        data = { 
            'listArts' : { 
                'clearlogo' : info.get('logo'), 
                'fanart' : info.get('fanart'), 
                'banner' : info.get('banner'), 
                'tvshow.poster': info.get('banner'), 
                'season.poster': info.get('banner'), 
                'tvshow.banner': info.get('banner'), 
                'season.banner': info.get('banner') 
                }, 
            'listInfos' : { 
                'video' : { 
                    'sorttitle': info.get('name'),
                    'plot' : info.get('description'), 
                    'year' : info.get('year'),
                    'mediatype' : 'tvshow',
                    'studio': 'ABS-CBN', 
                    'duration': info.get('duration', 0), 
                    'rating': info.get('rating', 0), 
                    'votes': info.get('votes', 0), 
                    } 
                },
            'contextMenu' : contextMenu
            }
        
        if info.get('casts', False):    
            data['listCasts'] = info.get('casts')
        
        return logger.logDebug(data)
            
    def formatVideoInfo(self, info, addToList=True, options = {}):

        contextMenu = {}
        if info.get('bandwidth') == None:
            # add to mylist / remove from mylist
            add = { control.lang(30300) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.ADDTOLIST, info.get('title'), query='ltype=%s&type=%s' % (info.get('ltype'), info.get('ltype'))) } 
            remove = { control.lang(30301) : 'XBMC.Container.Update(%s)' % self.generateActionUrl(str(info.get('id')), config.REMOVEFROMLIST, info.get('title'), query='ltype=%s&type=%s' % (info.get('ltype'), info.get('ltype'))) } 
            if addToList == True: 
                contextMenu.update(add)
            else:
                contextMenu.update(remove)

        data = { 
            'listArts' : { 
                'fanart' : info.get('fanart'), 
                'banner' : info.get('fanart')
                }, 
            'listProperties' : { 'IsPlayable' : 'true' } , 
            'listInfos' : { 
                'video' : { 
                    'sorttitle' : info.get('dateaired'), 
                    'tvshowtitle' : info.get('show'), 
                    'episode' : info.get('episodenumber'), 
                    'tracknumber' : info.get('episodenumber'), 
                    'plot' : info.get('description'), 
                    'aired' : info.get('dateaired'), 
                    'premiered' : info.get('dateaired'), 
                    'year' : info.get('year'), 
                    'mediatype' : info.get('type'),
                    'studio': 'ABS-CBN', 
                    'duration': info.get('duration', 0), 
                    'rating': info.get('rating', 0), 
                    'votes': info.get('votes', 0)
                    } 
                },
            'contextMenu' : contextMenu
            }

        if info.get('showObj', False):
            data['listArts'].update({
                'poster': info.get('showObj').get('banner'), 
                'tvshow.banner': info.get('showObj').get('banner'), 
                'season.banner': info.get('showObj').get('banner'),
                'tvshow.poster': info.get('showObj').get('banner'), 
                'season.poster': info.get('showObj').get('banner')
                })
            data['listInfos']['video'].update({
                'genre': info.get('showObj').get('parentname'),
                })
            if info.get('showObj').get('casts', False):    
                data['listCasts'] = info.get('showObj').get('casts')
        
        return logger.logDebug(data)
            
    def addDirectoryItem(self, name, url, mode, thumbnail, page=1, isFolder=True, query='', **kwargs):
        u = self.generateActionUrl(url, mode, name, thumbnail, page, query)
        liz = control.item(label=name)
        liz.setInfo(type="Video", infoLabels={"Title": name})
        liz.setArt({'icon':"DefaultFolder.png", 'thumb':thumbnail})
        for k, v in kwargs.items():
            if k == 'listProperties':
                for listPropertyKey, listPropertyValue in v.items():
                    liz.setProperty(listPropertyKey, listPropertyValue)
            if k == 'listInfos':
                for listInfoKey, listInfoValue in v.items():
                    liz.setInfo(listInfoKey, listInfoValue)
            if k == 'listArts':
                liz.setArt(v)
            if k == 'listCasts':
                try:liz.setCast(v)
                except:pass
            if k == 'contextMenu':
                menuItems = []
                for label, action in v.items():
                    menuItems.append((label, action))
                if len(menuItems) > 0: liz.addContextMenuItems(menuItems)
        return control.addItem(handle=thisPlugin, url=u, listitem=liz, isFolder=isFolder)

    def generateActionUrl(self, url, mode, name=None, thumbnail='', page=1, query=''):
        url = '%s?url=%s&mode=%s' % (sysaddon, quote_plus(url), str(mode))
        try: 
            if name != None: url += '&name=%s' % quote_plus(name)
        except: 
            pass
        try: 
            if int(page) >= 0: url += '&page=%s' % str(page)
        except: 
            pass
        try: 
            if thumbnail != '': url += '&thumbnail=%s' % quote_plus(thumbnail)
        except: 
            pass    
        try: 
            if query != '' and query != None: 
                if isinstance(query, dict): query = urlencode(query)
                url += "&" + query
        except: 
            pass
        return logger.logDebug(url)

    def endDirectory(self, cacheToDisc=True):
        control.directory(int(sys.argv[1]), cacheToDisc=cacheToDisc)


