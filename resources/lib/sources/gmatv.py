# -*- coding: utf-8 -*-

'''
    GMA.tv Add-on
    Copyright (C) 2020 cmik
'''

import os,sys,re,ssl,json,datetime,time,hashlib
import http.cookiejar as cookielib
import inputstreamhelper
from unidecode import unidecode
from urllib import request as libRequest
from urllib.parse import urlencode,quote,quote_plus
from operator import itemgetter
from resources import config
from resources.lib.libraries import control,cache
from resources.lib.models import episodes,shows,library,showcast

bs = control.soup
logger = control.logger

# Load DB
episodeDB = episodes.Episode(control.episodesFile)
showDB = shows.Show(control.showsFile)
libraryDB = library.Library(control.libraryFile)
castDB = showcast.ShowCast(control.celebritiesFile)

Logged = False

#---------------------- FUNCTIONS ----------------------------------------                  
def playEpisode(id, name, thumbnail, bandwidth=False):
    logger.logInfo('called function with param (%s)' % id)
    # control.showNotification(control.lang(30005), control.lang(30008))
    # control.execute('RunPlugin(plugin://plugin.video.youtube/play/?video_id=%s)' % id)
    episodeDetails = getMediaInfo(id, name, thumbnail, bandwidth)
    logger.logDebug(episodeDetails)
    if episodeDetails and 'errorCode' in episodeDetails and episodeDetails['errorCode'] == 0 and 'data' in episodeDetails:
        episode = episodeDetails.get('data')
        logger.logInfo(episode.get('plot'))
        liz = control.item(name, path='plugin://plugin.video.youtube/play/?video_id=%s' % episode.get('videoID'))
        liz.setArt({'thumb':episode.get('image'), 'icon':"DefaultVideo.png"})
        liz.setInfo(type='video', infoLabels={
            'title': name, 
            'sorttitle' : episode.get('dateaired'),
            'tvshowtitle' : episode.get('show'),
            'genre' : episode.get('parentname'),
            'episode' : episode.get('episodenumber'),
            'tracknumber' : episode.get('episodenumber'),
            'plot' : episode.get('plot'),
            'aired' : episode.get('dateaired'),
            'year' : episode.get('year'),
            'mediatype' : episode.get('ltype') 
            })
        
        liz.setProperty('fanart_image', episodeDetails['data']['fanart'])
        liz.setProperty('IsPlayable', 'true')
        try: 
            return control.resolve(thisPlugin, True, liz)
        except: 
            control.showNotification(control.lang(37032), control.lang(30004))
    return False
    
def getMediaInfo(episodeId, title, thumbnail, bandwidth=False):
    logger.logInfo('called function')
    mediaInfo = { 'errorCode' : 0 }

    res = episodeDB.get(int(episodeId))
    if len(res) == 1:
        episode = res[0] 
        res = showDB.get(episode.get('parentid'))
        show = res[0] if len(res) == 1 else {}
        
        mediaInfo['data'] = {}
        mediaInfo['data']['parentalAdvisory'] = False
        mediaInfo['data']['preview'] = False
        mediaInfo['data']['videoID'] = episode.get('url')
        mediaInfo['data']['show'] = show.get('name', episode.get('show', ''))
        mediaInfo['data']['parentname'] = show.get('parentname', '')
        mediaInfo['data']['rating'] = show.get('rating', episode.get('rating' , 0))
        if mediaInfo['data']['rating'] == None: mediaInfo['data']['rating'] = 0
        mediaInfo['data']['votes'] = show.get('votes', episode.get('votes' , 0))
        if mediaInfo['data']['votes'] == None: mediaInfo['data']['votes'] = 0
        mediaInfo['data']['plot'] = episode.get('description')
        mediaInfo['data']['image'] = episode.get('image', thumbnail)
        mediaInfo['data']['fanart'] = show.get('fanart', episode.get('fanart'))
        mediaInfo['data']['ltype'] = 'episode'
        mediaInfo['data']['dateaired'] = episode.get('dateaired')
        mediaInfo['data']['date'] = episode.get('dateaired')
        mediaInfo['data']['year'] = episode.get('year')
        mediaInfo['data']['episodenumber'] = episode.get('episodenumber')
        mediaInfo['data']['duration'] = 0
        mediaInfo['data']['views'] = episode.get('views', 0)
        mediaInfo['data']['showObj'] = show
        
        logger.logDebug(mediaInfo)

        episodeDB.update({'id' : episode.get('id'), 'views' : episode.get('views', 0) + 1})
        if 'id' in show:
            showDB.update({'id' : show.get('id'), 'views' : show.get('views', 0) + 1})
    else:
        mediaInfo['StatusMessage'] = 'Episode not found'
        mediaInfo['errorCode'] = 1
    return mediaInfo

def resetCatalogCache():
    logger.logInfo('called function')
    episodeDB.drop()
    showDB.drop()
    control.showNotification(control.lang(37039), control.lang(30010))
    reloadCatalogCache()

def reloadCatalogCache():
    logger.logInfo('called function')
    updateEpisodes = False
    if control.confirm('%s\n%s' % (control.lang(37035), control.lang(37036)), title=control.lang(30402)) == True:
        updateEpisodes = True
    if updateCatalogCache(updateEpisodes) is True:
        control.showNotification(control.lang(37003), control.lang(30010))
    else:
        control.showNotification(control.lang(37027), control.lang(30004))
    
def updateCatalogCache(loadEpisodes=False):
    logger.logInfo('called function')
    control.showNotification(control.lang(37015), control.lang(30005))
    cache.longCache.cacheClean(True) 
    cache.shortCache.cacheClean(True)
    
    # checkElaps = lambda x, y: x = time.time()-x if (time.time()-x) > y else x
    elaps = start = time.time()
    
    try:
        # update sections cache
        # if control.setting('displayWebsiteSections') == 'true':
            # control.showNotification(control.lang(37013))
            # sections = cache.sCacheFunction(getWebsiteHomeSections)
            # for section in sections:
                # cache.sCacheFunction(getWebsiteSectionContent, section['id'])
        
        # update sections cache
        control.showNotification(control.lang(37014), control.lang(30005))
        sections = getWebsiteHomeSections()
        nbCat = len(sections)
        i = 0
    except Exception as e:
        logger.logError('Can\'t update the catalog : %s' % (str(e)))
        return False
        
    for cat in sections:
        nbShow = 0
        try: 
            shows = getWebsiteSectionContent(cat['id'])
            nbShow = len(shows)
        except Exception as ce:
            logger.logError('Can\'t update category %s : %s' % (cat['id'], str(ce)))
            continue
        k = 0
        for s in shows:
            try: 
                if loadEpisodes: episodes = getEpisodesPerPage(s['id'], -1, s['year'], 1)
                else: show = getShow(s['id'], -1, s['year'])
            except Exception as se: 
                logger.logError('Can\'t update show %s : %s' % (s['id'], str(se)))
                k+=1
                continue
            k+=1
            
            elaps = time.time()-start 
            if elaps > 5:
                start = time.time()
                catpercent = 100 * i / nbCat
                cat1percent = 100 * 1 / nbCat
                showpercent = 100 * k / nbShow
                percent = catpercent + (cat1percent * (showpercent / 100) / 100)
                logger.logNotice('Updating catalog... %s' % (str(percent)+'%'))
                logger.logNotice(str(percent)+'%')
                control.infoDialog('Updating catalog... %s' % (str(percent)+'%'), heading=control.lang(30005), icon=control.addonIcon(), time=10000)
        i+=1
        
    return True
    
def getSiteMenu():
    logger.logInfo('called function')
    data = []
    
    html = bs(callServiceApi(config.uri.get('base'), base_url = config.websiteUrl), 'html.parser')
    menu = html.find("div", attrs = { 'id' : 'main_nav_desk' }).get_text()
    
    for category in html.find_all("li", attrs = { 'class' : 'has_children' }):
        
        subCategories = []
        name = category.a.get_text()
        id = category.a['data-id']
        url = category.a['href']
        
        for subcat in category.find("ul", attrs = { 'class' : 'menu_item' }).li:
            subcatname = subcat.a.get_text()
            subcaturl = subcat.a['href']
            id = re.compile('/([0-9]+)/', re.IGNORECASE).search(subcaturl).group(1)
        
            subCategories.append({
                'id' : str(id), 
                'name' : subcatname, 
                'url' : subcaturl
                })
        
        data.append({
            'id' : str(id), 
            'name' : name, 
            'url' : url, 
            'subcat' : subCategories
            })
    return data
    
def getCategories():
    logger.logInfo('called function')
    data = getSiteMenu()
    return data
    
def getSubCategories(categoryId):
    logger.logInfo('called function')
    data = []
    categoryData = getSiteMenu()
    for c in categoryData:
        if str(c['id']) == categoryId:
           data = c['subcat']
           break
    return data
    
def getMyListCategories():
    logger.logInfo('called function')
    url = config.uri.get('myList')
    html = callServiceApi(url, useCache=False)
    cache.shortCache.delete('mylistShowLastEpisodes')
    return extractListCategories(html)
    
def getMylistCategoryItems(id):
    logger.logInfo('called function')
    url = config.uri.get('myList')
    html = callServiceApi(url, useCache=False)
    return extractListCategoryItems(html, id)

def getMylistShowLastEpisodes():
    logger.logInfo('called function')
    data = []
    key = 'mylistShowLastEpisodes-%s' % datetime.datetime.now().strftime('%Y%m%d%H')
    logger.logInfo(key)
    if cache.shortCache.get(key) == '':
        url = config.uri.get('myList')
        html = bs(callServiceApi(url, useCache=False), 'html.parser')

        content = html.find("section", attrs = { 'id' : 'mylist-shows' }).find("ul", attrs = { 'class' : 'og-grid tv-programs-grid' })
        if content:
            for item in content.find_all("li"):
                url = item.a['href']
                if '/show/' in url:
                    show = extractMyListShowData(url, item)
                    (episodes, n) = getEpisodesPerPage(show.get('id'), show.get('parentid'), show.get('year', ''), 1, 1)
                    data.append(episodes.pop())

            cache.shortCache.set(key, json.dumps(data))
    else:
        data = json.loads(cache.shortCache.get(key).replace('\\\'', '\''))

    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)

def extractListCategoryItems(html, id):   
    logger.logInfo('called function')
    data = []
    
    html = bs(html, 'html.parser')
    content = html.find("section", attrs = { 'id' : id }).find("ul", attrs = { 'class' : 'og-grid tv-programs-grid' })
    if content:
        for item in content.find_all("li"):
            url = item.a['href']
            if '/show/' in url:
                data.append(extractMyListShowData(url, item))
            elif '/episode/' in url:
                data.append(extracMyListEpisodeData(url, item))
    
    return sorted(data, key=lambda item: item['title'] if 'title' in item else item['name'], reverse=False)
    
def extractMyListShowData(url, html):
    logger.logInfo('called function')
    showId = re.compile('/([0-9]+)/', re.IGNORECASE).search(url).group(1)
    res = showDB.get(int(showId))
    if len(res) == 1:
        return res[0]
    else:
        showName = html.find("div", attrs = { 'class' : 'show-cover-thumb-title-mobile sub-category' }).get_text()
        image = html.img['src']
        
        return {
            'type' : 'show',
            'ltype' : 'show',
            'id' : int(showId),
            'parentid' : -1,
            'parentname' : '',
            'name' : showName,
            'logo' : image,
            'image' : image,
            'fanart' : image,
            'banner' : image,
            'description' : '',
            'shortdescription' : '',
            'year' : '',
            'fanart' : image
            }

def extracMyListEpisodeData(url, html):
    logger.logInfo('called function')
    episodeId = re.compile('/([0-9]+)/', re.IGNORECASE).search(url).group(1)
    res = episodeDB.get(int(episodeId))
    if len(res) == 1:
        return res[0]
    else:
        showName = html.find("h2", attrs = { 'class' : 'show-cover-thumb-title-mobile sub-category' }).get_text()
        image = html.img['src']
        dateAired = html.find("h3", attrs = { 'class' : 'show-cover-thumb-title-mobile sub-category' }).get_text()
        
        year = ''
        episodeNumber = 0
        description = ''
        episodeName = ''
        
        if dateAired and len(dateAired) > 0:
            episodeName = dateAired[0].replace('AIRED:', '')
            year = episodeName.split(', ')[1]
            
        try:
            datePublished = datetime.datetime.strptime(episodeName, '%b %d, %Y')
        except TypeError:
            datePublished = datetime.datetime(*(time.strptime(episodeName, '%b %d, %Y')[0:6]))
        
        return {
            'id' : int(episodeId), 
            'parentid' : -1,
            'parentname' : '',
            'title' : '%s - %s' % (showName, episodeName), 
            'show' : showName, 
            'image' : image, 
            'episodenumber' : episodeNumber,
            'url' : url, 
            'description' : '',
            'shortdescription' : '',
            'dateaired' : episodeName,
            'date' : datePublished.strftime('%Y-%m-%d'),
            'year' : year,
            'fanart' : image,
            'ltype' : 'episode',
            'type' : 'episode'
            }
    
def extractListCategories(html):
    logger.logInfo('called function')
    data = []
    html = bs(html, 'html.parser')

    for li in html.nav.find_all("li"):
        name, count = li.a.get_text().split(' ', 1)
        data.append({
            'id' : li.a['href'].replace('#', ''),
            'name' : '%s (%s)' % (name, count)
            })
    # listCat = common.parseDOM(html, "section", attrs = { 'class' : 'sub-category-page' }, ret = 'id')
    # int(re.compile('/([0-9]+)/', re.IGNORECASE).search(url).group(1))
    return data
    
def getWebsiteSectionsData(forceUpdate=False):
    logger.logInfo('called function')
    data = []
    key = 'homeSECTION-%s' % datetime.datetime.now().strftime('%Y%m%d%H')
    if forceUpdate:
        cache.shortCache.delete(key)
    if cache.shortCache.get(key) == '':
        sectionList = callJsonApi(config.services.get('sections'), useCache=False)
        if 'shelves' in sectionList :
            shelves = sectionList.get('shelves')
            for shelf in shelves:
                if 'shelf_id' in shelf:
                    sectionData = callJsonApi(config.services.get('sectionDetails') % shelf.get('shelf_id'), useCache=False)
                    data.append({
                        'id' :  shelf.get('shelf_id'),
                        'name' : shelf.get('label'),
                        'shows' : sectionData.get('shows', {}),
                        })
            cache.shortCache.set(key, json.dumps(data))
    else:
        data = json.loads(cache.shortCache.get(key))
    return data

def getWebsiteHomeSections():   
    data = []
    sections = getWebsiteSectionsData(True)
    for section in sections:
        data.append({'id' : section.get('id'), 'name' : section.get('name')}) #, 'url' : '/', 'fanart' : ''})
    return data
    
def getWebsiteSectionContent(sectionId, page=1, itemsPerPage=8):
    logger.logInfo('called function')
    page -= 1
    data = []
    
    sections = getWebsiteSectionsData()
    for section in sections:
        if section.get('id') == sectionId: break
    
    index = itemsPerPage * page
    i = 0
    for show in section.get('shows', []):
        i += 1
        if i > index:
            data.append(extractWebsiteSectionShowData(show))
        if i >= (index + itemsPerPage):
            break
   
    # episodeDB.get([d.get('id') for d in data])
    return sorted(data, key=lambda item: item['name'], reverse=False)
    
def removeDuplicates(list):
    newList = []
    uniq = {}
    for d in list:
        key = '%s_%s'% (d.get('type'), str(d.get('id')))
        if key not in uniq: newList.append(d)
        uniq[key]=1
    return newList
    
def extractWebsiteSectionShowData(show):
    logger.logInfo('called function')
    
    showId = show.get('id', '')
    showName = unicodetoascii(show.get('show_title', ''))
    image = generateImageURL(show.get('primary_poster')[0].get('image_name'))
    description = unicodetoascii(show.get('synopsis', ''))
    year = show.get('airing_year', '')
    if year == '':
        try:
            datePublished = datetime.datetime.strptime(show.get('air_date_from'), '%m/%d/%Y')
        except TypeError:
            datePublished = datetime.datetime(*(time.strptime(show.get('air_date_from'), '%m/%d/%Y')[0:6]))
        year = datePublished.strftime('%Y')
    genre = show.get('keywords', '')
    
    res = showDB.get(int(showId))
    if len(res) == 1:
        return res[0]
    else:
        return {
            'type' : 'show',
            'ltype' : 'show',
            'id' : int(showId),
            'parentid' : -1,
            'parentname' : genre,
            'name' : showName,
            'logo' : image,
            'image' : image,
            'fanart' : image,
            'banner' : image,
            'url' : '',
            'description' : description,
            'shortdescription' : description,
            'year' : year
            }

def generateImageURL(image, type='poster', res='high'):
    img = 'image' 
    if type in 'poster':
        img = 'image' 
    elif type == 'banner':
        img = 'banner' 
    elif type == 'cast':
        img = 'cast' 
    elif type == 'episode':
        img = 'episode'
    return config.websiteCDNUrl + config.uri.get(img) % image

def getShows(subCategoryId, page = 1):
    logger.logInfo('called function with param (%s, %s)' % (subCategoryId, page))
    data = []
    subCategoryShows = []    
    
    html = bs(callServiceApi(config.uri.get('categoryList') % subCategoryId), 'html.parser')
    subCategoryShows.append(extractShows(html))
    
    pages = html.find('ul', attrs = { 'id' : 'pagination' }).find_all('a')
    if len(pages) > 1:
        for url in pages[1:]:
            subCategoryShows.append(extractShows(callServiceApi(url['href'])))
    
    if len(subCategoryShows) > 0:
        for sub in subCategoryShows:
            for d in sub:
                description = d['blurb'] if 'blurb' in d else ''
                dateAired = d['dateairedstr'] if 'dateairedstr' in d else ''
                res = showDB.get(int(d['id']))
                if len(res) == 1:
                    show = res[0]
                    show['parentid'] = int(subCategoryId)
                    show['parentname'] = d['parentname']
                    show['year'] = d['year']
                    show['casts'] = castDB.getByShow(int(d['id']))
                    data.append(show)
                else:
                    data.append({
                        'id' : int(d['id']),
                        'name' : d['name'],
                        'parentid' : int(subCategoryId),
                        'parentname' : d['parentname'],
                        'logo' : d['image'].replace(' ', '%20'),
                        'image' : d['image'].replace(' ', '%20'),
                        'fanart' : d['image'].replace(' ', '%20'),
                        'banner' : d['image'].replace(' ', '%20'),
                        'url' : d['url'],
                        'description' : d['description'],
                        'shortdescription' : d['shortdescription'],
                        'year' : d['year'],
                        'type' : 'show',
                        'ltype' : 'show'
                        })
                
    return data
    
def extractShows(html):
    logger.logInfo('called function')
    data = []
    list = html.find("ul", attrs = { 'id' : 'og-grid' })
    shows = list.find_all("li", attrs = { 'class' : 'og-grid-item-o' })
    dateaired = list.find("li", attrs = { 'class' : 'og-grid-item-o' })['data-aired']
    i = 0
    for show in shows:
        name = unicodetoascii(show.h2.get_text())
        aired = unicodetoascii(show.h3.get_text())
        image = show.img['src']
        url = show.a['href']
        id = re.compile('/([0-9]+)/').search(url).group(1)
        year = ''
        try: year = re.compile('^([0-9]{4})').search(dateaired[i]).group(1)
        except:
            try: year = aired.replace('AIRED: ', '').split(' ')[1]
            except: pass
        
        data.append({
            'id' : id,
            'parentid' : -1,
            'parentname' : '',
            'name' : name,
            'url' : url,
            'image' : image,
            'description' : '',
            'shortdescription' : '',
            'dateairedstr' : aired.replace('AIRED: ', ''),
            'year' : year
            })
        i+=1    
    return data

def getShow(showId, parentId=-1, year=''):
    logger.logInfo('called function with param (%s, %s, %s)' % (showId, str(parentId), year))
    data = {}
    import html
    showDetails = callJsonApi(config.services.get('showDetails') % showId, useCache=False)
    if showDetails.get('showabout', False) != False:
        showData = showDetails.get('showabout')[0]
        res = showDB.get(int(showData.get('show_id')))
        show = res[0] if len(res) == 1 else {}

        if year == '':
            try:
                datePublished = datetime.datetime.strptime(showData.get('air_date_from'), '%m/%d/%Y')
            except TypeError:
                datePublished = datetime.datetime(*(time.strptime(showData.get('air_date_from'), '%m/%d/%Y')[0:6]))
            year = datePublished.strftime('%Y')

        if parentId == -1: parentId = show.get('parentid', parentId)
        if year == '': year = show.get('year', year)
        
        url = config.websiteUrl + config.uri.get('base') + showData.get('url')
        logo = generateImageURL(showData.get('primary_poster')[0].get('image_name'), type='poster')
        image = generateImageURL(showData.get('secondary_poster')[0].get('image_name'), type='poster')
        fanart = generateImageURL(showData.get('main_tcard')[0].get('image_name'), type='banner')
        banner = fanart
            
        name = showData.get('show_title')
        description = cleanTextFromHTML(showData.get('synopsis'))
        genre = showData.get('keywords', '')
        
        actors = []
        if 'cast' in showDetails and len(showDetails.get('cast')) > 0:
            casts = callJsonApi(config.services.get('showCasts') % showId, useCache=False)
            i = 1
            for cast in casts:
                castId = cast.get('cast_id')
                castName = cast.get('artist_name')
                castRole = cast.get('character_name')
                castUrl = ''
                castImage = generateImageURL(cast.get('thumbnail'), type='cast')
                actors.append({
                    'castid': int(castId), 
                    'showid': int(showId), 
                    'name': castName, 
                    'role': castRole, 
                    'thumbnail': castImage, 
                    'order': i, 
                    'url': castUrl
                    })
                castDB.set(actors)
                i+=1
        
        # retrieve episodes list
        episodeList = getShowEpisodes(showId)

        data = {
            'id' : int(showId),
            'name' : name,
            'parentid' : int(parentId),
            'parentname' : genre,
            'logo' : logo,
            'image' : image,
            'fanart' : fanart,
            'banner' : banner,
            'url' : url,
            'description' : description,
            'shortdescription' : description,
            'year' : year,
            'nbEpisodes' : episodeList.get('nbEpisodes', 0),
            'episodes' : episodeList.get('episodes', []),
            'casts' : actors,
            'ltype' : 'show',
            'duration' : 0,
            'views' : 0,
            'rating' : 0,
            'votes' : 0,
            'type': 'show'
            }
        if episodeList.get('fromBase', False) == False:
            showDB.set(data)
    else:
        logger.logWarning('Error on show %s: %s' % (showId, 'no data found'))
    return data

def getShowEpisodes(showId):
    logger.logInfo('called function with param (%s)' % (showId))
    data = {
        'nbEpisodes': 0,
        'episodes': [],
        'fromBase': False
        }
    episodesList = []
    nbEpisodePages = callJsonApi(config.services.get('showNbFullEpisodePages') % showId, useCache = False)
    nbPages = 0
    fromBase = False
    if 'count' in nbEpisodePages:
        if nbEpisodePages.get('count') != 'all':
            nbPages = int(nbEpisodePages.get('count'))
            for page in range(1, nbPages+1, 1):
                pageData = callJsonApi(config.services.get('fullEpisodesPerPage') % (showId, page), useCache = False)
                if 'status' in pageData and pageData.get('status') == '200':
                    episodesList += pageData.get('data')
        else:
            pageData = callJsonApi(config.services.get('fullEpisodesPerPage') % (showId, 'all'), useCache = False)
            if 'status' in pageData and pageData.get('status') == '200':
                episodesList += pageData.get('data')
            else:
                episodesList = episodeDB.getByShow(showId, 500)
                fromBase = True
                data['fromBase'] = True
                data['episodes'] = episodesList

    data['nbEpisodes'] = len(episodesList)

    if len(episodesList) > 0 and not fromBase:
        for episode in episodesList:
            epNb = re.compile('Episode +([0-9]+)', re.IGNORECASE).search(episode.get('title'))
            try:
                datePublished = datetime.datetime.strptime(episode.get('publish_date'), '%B %d, %Y')
            except TypeError:
                datePublished = datetime.datetime(*(time.strptime(episode.get('publish_date'), '%B %d, %Y')[0:6]))
            year = datePublished.strftime('%Y')
            description = cleanTextFromHTML(episode.get('lead'))
            data['episodes'].append({
                'id' : episode.get('id'),
                'title' : episode.get('title'),
                'episodenumber' : int(epNb.group(1)) if epNb != None  else 0,
                'description' : description,
                'shortdescription' : description,
                'url' : episode.get('video').get('youtube'),
                'img' : generateImageURL(episode.get('photo').get('url'), type='episode'),
                'aired' : datePublished.strftime('%Y-%m-%d'),
                })

    return data
      
def getEpisodesPerPage(showId, parentId, year, page=1, itemsPerPage=8, order='desc'):
    logger.logInfo('called function with param (%s, %s, %s, %s, %s)' % (showId, parentId, year, page, itemsPerPage))
    data = []
    
    showDetails = getShow(showId, parentId, year)

    hasNextPage = False

    if showDetails:
        nbEpisodes = showDetails.get('nbEpisodes', 0)
        
        # if movie or special
        if nbEpisodes == 1 and showDetails.get('ltype', '') in ('movie', 'episode'):
            html = callServiceApi(config.uri.get('showDetails') % showId, useCache=False)
            episodeId = int(re.compile('var dfp_e = "(.+)";', re.IGNORECASE).search(html).group(1))
            episodeData = json.loads(re.compile('var ldj = (\{.+\})', re.IGNORECASE).search(html).group(1))

            res = episodeDB.get(episodeId)
            if len(res) == 1:
                e = res[0]
                if episodeData:
                    e['title'] = episodeData.get('name')
                    e['episodenumber'] = episodeData.get('episodenumber')
                    e['showObj'] = showDetails
                data.append(e)
            else:
                try:
                    datePublished = datetime.datetime.strptime(episodeData.get('datePublished'), '%Y-%m-%d')
                except TypeError:
                    datePublished = datetime.datetime(*(time.strptime(episodeData.get('datePublished'), '%Y-%m-%d')[0:6]))
        
                type = 'episode' if episodeData.get('@type' ,'episode').lower() not in ('episode','movie') else episodeData.get('@type' ,'episode').lower()
                edata = {
                    'id' : episodeId,
                    'title' : episodeData.get('name'),
                    'show' : showDetails.get('name', episodeData.get('name')),
                    'image' : episodeData.get('thumbnailUrl',  episodeData.get('image')),
                    'episodenumber' : 1,
                    'description' : episodeData.get('description'),
                    'shortdescription' : episodeData.get('description'),
                    'dateaired' : datePublished.strftime('%b %d, %Y'),
                    'date' : datePublished.strftime('%Y-%m-%d'),
                    'year' : datePublished.strftime('%Y'),
                    'fanart' : showDetails.get('fanart'),
                    'showObj' : showDetails,
                    'ltype' : type,
                    'duration' : 0,
                    'views' : 0,
                    'rating' : episodeData.get('aggregateRating' , {}).get('ratingValue', 0),
                    'votes' : episodeData.get('aggregateRating' , {}).get('reviewCount', 0),
                    'type' : 'episode'
                    }
                if edata['rating'] == None: edata['rating'] = 0
                if edata['votes'] == None: edata['votes'] = 0
                duration = re.compile('^([0-9]+)h([0-9]*)[m]?|([0-9]+)m$', re.IGNORECASE).search(episodeData.get('duration', episodeData.get('timeRequired', 0)))
                if duration: 
                    if duration.group(1) != None: 
                        if duration.group(2) != '': edata['duration'] = int(duration.group(2))
                        edata['duration'] += int(duration.group(1)) * 60
                    elif duration.group(3) != None: 
                        edata['duration'] = int(duration.group(3))
                data.append(edata)
        else:
            episodes = sorted(showDetails.get('episodes'), key=lambda item: item['episodenumber'], reverse=True if order == 'desc' else False)

            # Calculating episode index according to page and items per page
            episodeIndex = (page * 1 - 1) * itemsPerPage
            for index in range(episodeIndex, episodeIndex+itemsPerPage, 1):
                if index >= nbEpisodes:
                    break

                logger.logDebug('Episode index : %s' % index)
                episodeData = episodes[index]
                url = episodeData.get('url')
                episodeId = int(episodeData.get('id'))
                res = episodeDB.get(episodeId)
                if len(res) == 1:
                    e = res[0]
                    # Update title value with episode number
                    if episodeData:
                        e['title'] = episodeData.get('title')
                        e['episodenumber'] = episodeData.get('episodenumber')
                        e['showObj'] = showDetails
                    data.append(e)
                else:
                    image = episodeData.get('img')
                    title = episodeData.get('title')
                    dateAired = episodeData.get('aired')
                    showTitle = showDetails.get('name')
                    fanart = showDetails.get('fanart')
                    year = dateAired.split('-').pop(0)
                    description = episodeData.get('description')
                    shortDescription = description
                    episodeNumber = episodeData.get('episodenumber')
                    
                    e = {
                        'id' : episodeId,
                        'title' : title,
                        'parentid' : int(showId),
                        'show' : showTitle,
                        'image' : image,
                        'fanart' : fanart,
                        'episodenumber' : episodeNumber,
                        'url' : url,
                        'description' : description,
                        'shortdescription' : shortDescription,
                        'dateaired' : dateAired,
                        'date' : dateAired,
                        'year' : year,
                        'parentalAdvisory' : '',
                        'showObj' : showDetails,
                        'ltype' : showDetails.get('ltype'),
                        'type' : 'episode'
                        }
                    episodeDB.set(e)
                    data.append(e)

    # return sorted(data, key=lambda episode: episode['title'], reverse=True)
    return (data, hasNextPage)
    
def addToMyList(id, name, ltype, type):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    url = config.uri.get('addToList')
    logger.logDebug(url)
    res = {}
    control.showNotification(control.lang(37026))

def removeFromMyList(id, name, ltype, type):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, ltype, type))
    url = config.uri.get('removeFromList')
    logger.logDebug(url)
    res = {}
    control.showNotification(control.lang(37026))
    
def showExportedShowsToLibrary():
    data = []
    temp = {}
    exported = libraryDB.getAll()
    for d in exported:
        if 'id' in d:
            temp[d.get('id')] = d
    if len(temp) > 0:
        shows = showDB.get(list(temp.keys()))
        for s in shows:
            temp[s.get('id')].update(s)
            data.append(temp.get(s.get('id')))
    return data

def removeFromLibrary(id, name):
    data = libraryDB.get(int(id))
    if len(data) > 0:
        if logger.logInfo(libraryDB.delete(data[0])):
            path = os.path.join(control.showsLibPath, name, '')
            logger.logInfo(path)
            if logger.logInfo(control.pathExists(path)): 
                if control.confirm('%s\n%s' % (control.lang(37041), control.lang(37042)), title=name) == False:
                    control.deleteFolder(path, True)
            control.showNotification(control.lang(37043) % name, control.lang(30010))
        else:
            control.showNotification(control.lang(37044), control.lang(30004))
    else:
        control.showNotification(control.lang(37045), control.lang(30001))


def addToLibrary(id, name, parentId=-1, year='', updateOnly=False):
    logger.logInfo('called function with param (%s, %s, %s, %s)' % (id, name, parentId, year))
    from resources.lib.indexers import navigator
    status = True
    updated = False
    nbUpdated = 0
    nbEpisodes = int(control.setting('exportLastNbEpisodes'))
    (episodes, n) = getEpisodesPerPage(id, parentId, year, page=1, itemsPerPage=nbEpisodes)
    
    if len(episodes) > 0:
    
        path = os.path.join(control.showsLibPath, name)
        control.makePath(path)
        
        # Show NFO file
        try: 
            e = episodes[0]
            show = e.get('showObj')
            res = libraryDB.get(show.get('id'))
            lib = res[0] if len(res) == 1 else {}
            control.writeFile(logger.logNotice(str(os.path.join(path, 'tvshow.nfo'))), str(generateShowNFO(show, path)))
        except Exception as err:
            logger.logError(err)
            status = False
        
        if status == True:
            
            mostRecentDate = lastDate = lib.get('date', datetime.datetime(1900, 1, 1))
            lastCheck = lib.get('lastCheck', datetime.datetime(1900, 1, 1))
            logger.logNotice('last check date : %s' % lastCheck.strftime('%Y-%m-%d %H:%M:%S'))
            for e in sorted(episodes, key=lambda item: item['date'], reverse=False):
                filePath = os.path.join(path, '%s.strm' % e.get('title').replace('|', '-'))

                logger.logNotice('episode date : %s' % e.get('date'))
                try:
                    episodeDate = datetime.datetime.strptime(e.get('date'), '%Y-%m-%d')
                except TypeError:
                    episodeDate = datetime.datetime(*(time.strptime(e.get('date'), '%Y-%m-%d')[0:6]))
                
                if lastDate.date() < episodeDate.date():
                    updated = True
                    nbUpdated += 1
                    if mostRecentDate.date() < episodeDate.date(): mostRecentDate = episodeDate
                    
                if not updateOnly or updated:
                    try:
                        # Episode STRM / NFO files
                        control.writeFile(logger.logNotice(os.path.join(path, '%s.nfo' % e.get('title').replace('|', '-'))), generateEpisodeNFO(e, path, filePath))
                        control.writeFile(logger.logNotice(filePath), navigator.navigator().generateActionUrl(str(e.get('id')), config.PLAY, '%s - %s' % (e.get('show'), e.get('dateaired')), e.get('image')))
                    except Exception as err:
                        logger.logError(err)
                        status = False
                        break
    else: 
        status = False
            
    if status == True: 
        if not updateOnly: control.showNotification(control.lang(37034) % name, control.lang(30010))
        libraryDB.set({'id' : int(show.get('id')), 
            'name' : show.get('name'), 
            'parentid' : int(show.get('parentid')),
            'year' : show.get('year'),
            'date' : mostRecentDate.strftime('%Y-%m-%d')
            })
    else: 
        if not updateOnly: control.showNotification(control.lang(37033), control.lang(30004))
    return {'status': status, 'updated': updated, 'nb': nbUpdated}

def generateShowNFO(info, path):
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('name')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('name')
    nfoString += '<episode>%s</episode>' % info.get('nbEpisodes')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb aspect="poster">%s</thumb>' % info.get('image')
    nfoString += '<fanart url=""><thumb dim="1280x720" colors="" preview="%s">%s</thumb></fanart>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<genre>%s</genre>' % info.get('parentname')
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath></filenameandpath>'
    nfoString += '<basepath>%s</basepath>' % path
    for c in info.get('casts', []):
        nfoString += '<actor><name>%s</name><order>%d</order><thumb>%s</thumb></actor>' % (c.get('name'), c.get('order'), c.get('thumbnail'))
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by GMA.tv addon --> \
<tvshow> \
    %s \
</tvshow>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)
    
def generateEpisodeNFO(info, path, filePath):
    logger.logInfo('called function')
    nfoString = ''
    nfoString += '<title>%s</title>' % info.get('title')
    nfoString += '<showtitle>%s</showtitle>' % info.get('show')
    nfoString += '<sorttitle>%s</sorttitle>' % info.get('dateaired')
    nfoString += '<episode>%s</episode>' % info.get('episodenumber')
    nfoString += '<plot>%s</plot>' % info.get('description')
    nfoString += '<aired>%s</aired>' % info.get('dateaired')
    nfoString += '<year>%s</year>' % info.get('year')
    nfoString += '<thumb>%s</thumb>' % info.get('image')
    nfoString += '<art><banner>%s</banner><fanart>%s</fanart></art>' % (info.get('fanart'), info.get('fanart'))
    nfoString += '<path>%s</path>' % path
    nfoString += '<filenameandpath>%s</filenameandpath>' % filePath
    nfoString += '<basepath>%s</basepath>' % filePath
    nfoString += '<studio>ABS-CBN</studio>'
    
    return u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?> \
<!-- created on %s - by GMA.tv addon --> \
<episodedetails> \
    %s \
</episodedetails>' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nfoString)

def checkLibraryUpdates(quiet=False):
    logger.logInfo('called function')
    items = libraryDB.getAll()
    for show in items:
        logger.logNotice('check for update for show %s' % show.get('name'))
        result = addToLibrary(show.get('id'), show.get('name'), show.get('parentid'), show.get('year'), updateOnly=True)
        if result.get('updated') == True:
            logger.logNotice('Updated %s episodes' % str(result.get('nb')))
            if not quiet: control.showNotification(control.lang(37037) % (str(result.get('nb')), show.get('name')), control.lang(30011))
        else:
            logger.logNotice('No updates for show %s' % show.get('name'))
    return True
    
def enterSearch(category, type):
    logger.logInfo('called function with params (%s, %s)' % (category, type))
    data = []
    search = control.inputText(control.lang(30204)).strip()
    if len(search) >= 3:
        if category == 'movieshow':
            if type == 'title':
                data = showDB.searchByTitle(search)
            elif type == 'category':
                data = showDB.searchByCategory(search)
            elif type == 'year':
                data = showDB.searchByYear(search)
            elif type == 'cast':
                cast = castDB.searchByActorName(search)
                data = showDB.get([c.get('showid') for c in cast])
        elif category == 'episode':
            if type == 'title':
                data = episodeDB.searchByTitle(search)
            elif type == 'date':
                data = episodeDB.searchByDate(search)
    else:
        control.showNotification(control.lang(37046), control.lang(30001))
    if data == []:
        control.showNotification(control.lang(37047), control.lang(30001))
    else:
        control.showNotification(control.lang(37048) % len(data), control.lang(30001))
    return data
    
def getFromCookieByName(string, startWith=False):
    logger.logInfo('called function')
    global cookieJar
    cookieObj = None
    
    for c in cookieJar:
        if (startWith and c.name.startswith(string)) or (not startWith and c.name == string) :
            cookieObj = c
            break
                
    return cookieObj
    
def getCookieContent(filter=False, exceptFilter=False):
    logger.logInfo('called function')
    global cookieJar
    cookie = []
    for c in cookieJar:
        if (filter and c.name not in filter) or (exceptFilter and c.name in exceptFilter):
            continue
        cookie.append('%s=%s' % (c.name, c.value))
    return cookie

def checkIfError(html):
    error = False
    message = ''
    if html == '' or html == None:
        error = True
        message = control.lang(37029)
    else:
        t = bs(html, 'html.parser').title
        if t:
            if 'Error' in t:
                error = True
                message = t.get_text().split(' | ')[1]
    return { 'error' : error, 'message' : message }

def callServiceApi(path, params={}, headers=[], base_url=config.websiteUrl, useCache=True, jsonData=False, returnMessage=True):
    logger.logInfo('called function with param (%s)' % (path))
    global cookieJar
    
    res = {}
    cached = False
    toCache = False
    
    # No cache if full response required
    if returnMessage == False:
        useCache = False
    
    key = config.urlCachePrefix + cache.generateHashKey(base_url + path + urlencode(params))
    logger.logDebug('Key %s : %s - %s' % (key, base_url + path, params))
    
    if useCache == True:
        tmp = cache.shortCache.getMulti(key, ['url', 'timestamp'])
        if (tmp == '') or (tmp[0] == '') or (time.time()-float(tmp[1])>int(control.setting('cacheTTL'))*60):
            toCache = True
            logger.logInfo('No cache for (%s)' % key)
        else:
            cached = True
            res['message'] = logger.logDebug(tmp[0])
            logger.logInfo('Used cache for (%s)' % key)
    
    if cached is False:
        opener = libRequest.build_opener(libRequest.HTTPRedirectHandler(), libRequest.HTTPCookieProcessor(cookieJar))
        userAgent = config.userAgents[base_url] if base_url in config.userAgents else config.userAgents['default']
        headers.append(('User-Agent', userAgent))
        headers.append(('Accept-encoding', 'gzip'))
        headers.append(('Connection', 'keep-alive'))
        opener.addheaders = headers
        logger.logDebug('### Request headers, URL & params ###')
        logger.logDebug(headers)
        logger.logDebug('%s - %s' % (base_url + path, params))
        requestTimeOut = int(control.setting('requestTimeOut')) if control.setting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                if jsonData == True:                    
                    request = libRequest.Request(base_url + path)
                    request.add_header('Content-Type', 'application/json')
                    response = opener.open(request, json.dumps(params).encode("utf-8"), timeout = requestTimeOut)
                else:
                    data_encoded = urlencode(params).encode("utf-8")
                    response = opener.open(base_url + path, data_encoded, timeout = requestTimeOut)
            else:
                response = opener.open(base_url + path, timeout = requestTimeOut)
                
            logger.logDebug('### Response headers ###')
            logger.logDebug(response.geturl())
            logger.logDebug('### Response redirect URL ###')
            logger.logDebug(response.info())
            logger.logDebug('### Response ###')
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                res['message'] = gzip.decompress(response.read())
            else:
                res['message'] = response.read() if response else ''
            res['status'] = int(response.getcode())
            res['headers'] = response.info()
            res['url'] = response.geturl()
            logger.logDebug(res)
        except (libRequest.URLError, ssl.SSLError) as e:
            logger.logError(e)
            message = '%s : %s' % (e, base_url + path)
            # message = "Connection timeout : " + base_url + path
            logger.logSevere(message)
            control.showNotification(message, control.lang(30004))
            # No internet connection error
            if 'Errno 11001' in message:
                logger.logError('Errno 11001 - No internet connection')
                control.showNotification(control.lang(37031), control.lang(30004), time=5000)
            toCache = False
            pass
        
        if toCache == True and res:
            value = res.get('message') if re.compile('application/json', re.IGNORECASE).search('|'.join(res['headers'].keys())) or re.compile('binary/octet-stream', re.IGNORECASE).search('|'.join(res['headers'].values())) else repr(res.get('message'))
            cache.shortCache.setMulti(key, {'url': value, 'timestamp' : time.time()})
            logger.logDebug(res.get('message'))
            logger.logInfo('Stored in cache (%s) : %s' % (key, {'url': value, 'timestamp' : time.time()}))
    
    # Clear headers
    headers[:] = []
    
    if returnMessage == True:
        return res.get('message')
        
    return res

def callJsonApi(path, params={}, headers=[('X-Requested-With', 'XMLHttpRequest')], base_url=config.webserviceUrl, useCache=True, jsonData=False):
    logger.logInfo('called function')
    data = {}
    res = callServiceApi(path, params, headers, base_url, useCache, jsonData)
    try:
        data = json.loads(res) if res != '' else []
    except:
        pass
    return data

def cleanTextFromHTML(text):
    import html
    return html.unescape(bs(text, 'html.parser').text)

def unicodetoascii(text):
    try:
        return unidecode(text)
    except:
        logger.logError(text)
        return text
        
# This function is a workaround to fix an issue on cookies conflict between live stream and shows episodes
def cleanCookies(notify=True):
    logger.logInfo('called function')
    message = ''
    if os.path.exists(os.path.join(control.homePath, 'cache', 'cookies.dat'))==True:  
        logger.logInfo('cookies file FOUND (cache)')
        try: 
            os.unlink(os.path.join(control.homePath, 'cache', 'cookies.dat'))
            message = control.lang(37004)
        except: 
            message = control.lang(37005)
                
    elif os.path.exists(os.path.join(control.homePath, 'temp', 'cookies.dat'))==True:  
        logger.logInfo('cookies file FOUND (temp)')
        try: 
            os.unlink(os.path.join(control.homePath, 'temp', 'cookies.dat'))
            message = control.lang(37004)
        except: 
            message = control.lang(37005)
    elif os.path.exists(os.path.join(control.dataPath, config.cookieFileName))==True:  
        logger.logInfo('cookies file FOUND (profile)')
        try: 
            os.unlink(os.path.join(control.dataPath, config.cookieFileName))
            message = control.lang(37004)
        except: 
            message = control.lang(37005)
    else:
        message = control.lang(37006)
        
    if notify == True:
        control.showNotification(message)
    
#---------------------- MAIN ----------------------------------------
thisPlugin = int(sys.argv[1])
    
cookieJar = cookielib.CookieJar()
cookieFile = ''
cookieJarType = ''

if control.pathExists(control.dataPath):
    cookieFile = os.path.join(control.dataPath, config.cookieFileName)
    cookieJar = cookielib.LWPCookieJar(cookieFile)
    cookieJarType = 'LWPCookieJar'
    
if cookieJarType == 'LWPCookieJar':
    try:
        cookieJar.load()
    except:
        pass
    
if cookieJarType == 'LWPCookieJar':
    cookieJar.save()


