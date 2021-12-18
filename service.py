#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
    GMA Add-on
    Copyright (C) 2020 cmik
'''

import re,shutil,threading,ssl,time,xbmc,xbmcaddon
import http.cookiejar as cookielib
from six.moves import socketserver
from urllib import request as libRequest
from urllib.parse import quote,urlencode,urlparse,parse_qsl
from http.server import SimpleHTTPRequestHandler
from resources import config
from resources.lib.libraries import control

class ProxyHandler(SimpleHTTPRequestHandler):

    _cj = cookielib.LWPCookieJar()
    _user_agent = config.userAgents['default']
    _websiteUrl = config.websiteUrl
            
    def do_GET(self):
        xbmc.log('Requested GET: %s' % (self.path), level=xbmc.LOGDEBUG)
        if '/healthcheck' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
        else:
            query = self.getQueryParameters(self.path)
            if ('url' in query):
            
                requestHeaders = []
                requestHeaders.append(('User-Agent', self._user_agent))
                requestHeaders.append(('Accept', '*/*,akamai/media-acceleration-sdk;b=1702200;v=1.2.2;p=javascript'))
                requestHeaders.append(('Origin', self._websiteUrl))
                requestHeaders.append(('Referer', self._websiteUrl+'/'))
                requestHeaders.append(('Sec-Fetch-Mode', 'cors'))
                res = self.urlopen(query.get('url'), headers=requestHeaders)
                
                if (res.get('status')):
                    proxyUrlFormat = control.setting('proxyStreamingUrl')
                    content = re.sub(r'(http[^\s"]+)', lambda x: proxyUrlFormat % (control.setting('proxyHost'), control.setting('proxyPort'), urllib.quote(x.group(0))), res.get('body')) if ('amssabscbn.akamaized.net' not in query.get('url')) else res.get('body')
                    
                    self.send_response(res.get('status'))
                    for header, value in res.get('headers').items():
                        if (header.lower() == 'content-length'):
                            value = len(content)
                        if (header.lower() == 'set-cookie'):
                            netloc = urlparse(proxyUrlFormat).netloc
                            host = netloc.split(':')[0] if ':' in netloc else netloc
                            value = re.sub(r'path=[^;]+; domain=.+', 'path=/; domain=%s' % (host), value)
                        if (header.lower() in ('server', 'set-cookie')):
                            continue
                        self.send_header(header, value)
                    self.end_headers()
                    self.wfile.write(content)
                    self.wfile.close()
                else:
                    self.send_error(522)
            else:
                self.send_error(400)
                        
    def urlopen(self, url, params = {}, headers = []):        
        res = {}
        opener = libRequest.build_opener(libRequest.HTTPRedirectHandler(), libRequest.HTTPCookieProcessor(self._cj))
        opener.addheaders = headers
        requestTimeOut = int(xbmcaddon.Addon().getSetting('requestTimeOut')) if xbmcaddon.Addon().getSetting('requestTimeOut') != '' else 20
        response = None
        
        try:
            if params:
                data_encoded = urlencode(params)
                response = opener.open(url, data_encoded, timeout = requestTimeOut)
            else:
                response = opener.open(url, timeout = requestTimeOut)
                
            res['body'] = response.read() if response else ''
            res['status'] = response.getcode()
            res['headers'] = response.info()
            res['url'] = response.geturl()
        except (libRequest.URLError, ssl.SSLError) as e:
            message = '%s : %s' % (e, url)
            xbmc.log(message, level=xbmc.LOGERROR)
        
        return res
        
    def getQueryParameters(self, url):
        qparam = {}
        query = url.split('?')[1] if (len(url.split('?')) > 1) else None 
        if query:
            qparam = dict(parse_qsl(query.replace('?','')))
        return qparam 
        

class LibraryChecker():
    _status = True
    _scheduled = 60 * int(control.setting('librayCheckSchedule'))
        
    def checkLibraryUpdates(self):
        first = True
        start = time.time()
        while self._status:
            if ((time.time()-start) > int(self._scheduled)) or first:
                first = False
                start = time.time()
                control.run(config.CHECKLIBRARYUPDATES, 'service')
                time.sleep(10)
            
            
    def shutdown(self):
        self._status = False
        
if __name__ == "__main__":
    httpPort = int(control.setting('proxyPort'))
    server = socketserver.TCPServer(('', httpPort), ProxyHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    xbmc.log('[%s] Service: starting HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGINFO)
    
    libActive = True if control.setting('libraryAutoUpdate') == 'true' else False
    
    if libActive == True:
        libChecker = LibraryChecker()
        libSchedTask = threading.Thread(target=libChecker.checkLibraryUpdates)
        libSchedTask.start()
        xbmc.log('[%s] Service: starting library checker' % control.addonInfo('name'), level=xbmc.LOGINFO)
    
    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(10):
            # Abort was requested while waiting. We should exit
            break

    server.shutdown()
    server_thread.join()
    xbmc.log('[%s] - Service: stopping HTTP proxy server on port %s' % (control.addonInfo('name'), httpPort), level=xbmc.LOGINFO)
    if libActive == True: 
        libChecker.shutdown()
        libSchedTask.join()
        xbmc.log('[%s] - Service: stopping library checker' % control.addonInfo('name'), level=xbmc.LOGINFO)