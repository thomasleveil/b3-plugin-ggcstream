#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Courgette
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Changelog:
#
# 2011-04-27 - 0.1 
# * first release. Work for cod4
# 2011-04-29 - 0.2
# * add support for frostbite games bfbc2 and moh (tested)
# * add suuport for games cod, cod2, cod5, et and etpro (untested)
# 2011-06-04 - 1.0
# * B3 will only install the streaming service if GGC Stream reports an error.
# * the !ggcstream commands now ask the GGC server if our server is correctly
#   streaming
# 2011-10-24 - 1.1
# * Add support for Battlefield 3
# * GGC Stream installation is now run in a thread so it does not block B3
# * Makes sure only one installation occurs at once

from b3.events import EVT_UNKNOWN
import StringIO
import b3.plugin
import gzip
from socket import inet_aton
from struct import unpack
from threading import Timer, Thread, Lock
import time
import urllib2
from hashlib import sha1
import uuid
import json
from datetime import datetime

__version__ = '1.1'
__author__ = 'Courgette'


SUPPORTED_PARSERS = {
                     'bf3': 'bf3',
                     'bfbc2': 'bc2',
                     'moh': 'moh',
                     'cod': 'cod',
                     'cod2': 'cod2',
                     'cod4': 'cod4',
                     'cod5': 'codww',
                     'et': 'et',
                     'etpro': 'et'}

FROSTBITE_GAMES = ('bfbc2', 'moh', 'bf3')

USER_AGENT =  "B3 GGC STREAM plugin/%s" % __version__
GGCSTREAM_API_ID = "2"
GGCSTREAM_API_KEY = "6b3e20e3affa3978106bfe36ba9b332877599793"

class UnsupportedGameError(Exception):
    pass

#--------------------------------------------------------------------------------------------------
class GgcstreamPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _adminPlugin = None
    _frostbite_async_pb_msg = []
    remote_lastmodified = remote_etag = None
    _rconMethod = None
    _installing_lock = Lock()

    def onStartup(self):
        if self.console.gameName not in SUPPORTED_PARSERS:
            self.error("This game is not supported by this plugin")
            self.disable()
            return

        if self.console.gameName in FROSTBITE_GAMES:
            self._rconMethod = self._frostbitePbCmd
        else:
            self._rconMethod = self.console.write

        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        self._adminPlugin.registerCommand(self, "ggcstream", 100, self.cmd_ggcstream)
        
        Timer(10.0, self._check_if_installed).start()

        self.registerEvent(EVT_UNKNOWN)


    def onEvent(self, event):
        if self.console.gameName in FROSTBITE_GAMES and event.type == EVT_UNKNOWN:
            try:
                if event.data[0].startswith('PunkBuster Server:'):
                    self.onPunkbusterEvent(event.data[0])
            except IndexError:
                pass


    def cmd_ggcstream(self, data=None, client=None, cmd=None):
        """\
        check if the GGC Stream service is correctly setup
        """
        jsondata = self._queryGGCStreamService(self.console._publicIp, self.console._port)
        self.debug("%s:%s -> %r",self.console._publicIp, self.console._port, jsondata)
        if jsondata and not 'error' in jsondata:
            client.message("GGC Stream correctly set up")
            for k, v in jsondata.iteritems():
                if k == 'heartbeat':
                    client.message("Last heartbeat sent on %s" % datetime.fromtimestamp(jsondata['heartbeat']).strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    client.message("%s: %s" % (k, v))
        else:
            try:
                self._install_GGCStream(client=client)
                client.message("GGC Stream setup on this server")
            except UnsupportedGameError:
                client.message("this game is not supported")

    def _check_if_installed(self):
        jsondata = self._queryGGCStreamService(self.console._publicIp, self.console._port)
        self.debug("%s:%s -> %r",self.console._publicIp, self.console._port, jsondata)
        try:
            assert 'error' not in jsondata
            assert jsondata['registered'] == 1
            assert type(jsondata['server_id']) == int
            assert jsondata['server_id'] > 0
        except (AssertionError, KeyError), err:
            self.debug(repr(err))
            self._install_GGCStream()
            
    def _install_GGCStream(self, client=None):
        try:
            t = Thread(target=self._do_uconadd, kwargs={'gamecode':SUPPORTED_PARSERS[self.console.gameName], 'client':client}, name="GGCstream:_do_uconadd")
            t.daemon = True
            t.start()
        except KeyError, e:
            raise UnsupportedGameError(e)

    def _do_uconadd(self, gamecode=None, client=None):
        if not self._installing_lock.acquire(False):
            if client: client.message("already setting up GGC Stream. Try later")
        else:
            if client: client.message("Setting up GGC Stream...")
            try:
                # test presence of pbucon.use
                data = self._rconMethod("pb_sv_uconadd")
                if data and 'pbucon.use' in data:
                    # no pbucon.use file : we need to create it and restart pb
                    if client: client.message("creating pbucon.use file")
                    self.info(self._rconMethod("pb_sv_writecfg pbucon.use"))
                    self.info(self._rconMethod("pb_sv_restart"))
                    if client: client.message("restarting punkbuster, please wait...") 
                    time.sleep(20)
                if client: client.message("adding GGC Stream to punkbuster config")
                self.info(self._rconMethod("pb_sv_USessionLimit 9"))
                self.info(self._rconMethod("pb_sv_uconadd 1 85.214.107.154 ggc_85.214.107.154 %s" % gamecode))
                self.info(self._rconMethod("pb_sv_uconadd 1 85.214.107.155 ggc_85.214.107.155 %s" % gamecode))
                self.info(self._rconMethod("pb_sv_uconadd 1 85.214.107.156 ggc_85.214.107.156 %s" % gamecode))
                if client: client.message("saving punkbuster config")
                self.info(self._rconMethod("pb_sv_writecfg"))
            finally:
                self._installing_lock.release()

    def _frostbitePbCmd(self, command):
        """ send a punkbuster command and wait for the response """
        self._frostbite_async_pb_msg = []
        self.console.write(('punkBuster.pb_sv_command', command))
        starttime = time.time()
        while time.time()-starttime < 5:
            try:
                msg = self._frostbite_async_pb_msg.pop()
                return msg
            except IndexError:
                time.sleep(.1)
        return None


    def onPunkbusterEvent(self, data):
        self.debug("punbuster : %s", data)
        self._frostbite_async_pb_msg.append(data)


    def _queryUrl(self, url):
        self.info("querying %s" % url)
        try:
            req = urllib2.Request(url, None)
            req.add_header('User-Agent', USER_AGENT)
            req.add_header('Accept-encoding', 'gzip')
            opener = urllib2.build_opener()
            #self.debug('headers : %r', req.headers)
            webFile =  opener.open(req)
            data = webFile.read()
            webFile.close()
            if webFile.headers.get('content-encoding', '') == 'gzip':
                data = StringIO.StringIO(data)
                gzipper = gzip.GzipFile(fileobj=data)
                data = gzipper.read()
            self.remote_lastmodified = webFile.headers.get('Last-Modified') 
            self.remote_etag = webFile.headers.get('ETag') 
            #self.debug('received headers : %s', webFile.info())
            #self.debug("received %s bytes", len(data))
            return data
        except urllib2.URLError, err:
            self.remote_etag = self.remote_lastmodified = None
            return "%s"%err
        except IOError, e:
            self.remote_etag = self.remote_lastmodified = None
            if hasattr(e, 'reason'):
                return "%s" % e.reason
            elif hasattr(e, 'code'):
                return "error code: %s" % e.code
            self.debug("%s"%e)
            return "%s"%e

    def _queryGGCStreamService(self, ip, port):
        myUuid = uuid.uuid4()
        hashedkey = sha1("%s%s" % (GGCSTREAM_API_KEY, myUuid)).hexdigest() 
        url = "http://api.ggc-stream.com/public/server/heartbeat-ipport/ip/%(ip)s/port/%(port)s/key/%(api_id)s_%(hashed_key)s_%(uuid)s" % {
                            'ip': unpack('!L',inet_aton(ip))[0], 
                            'port': port,
                            'api_id': GGCSTREAM_API_ID,
                            'hashed_key': hashedkey,
                            'uuid': myUuid
                            }
        rawdata = self._queryUrl(url)
        try:
            jsondata = json.loads(rawdata)
        except ValueError:
            jsondata = {'error': rawdata}
        return jsondata

if __name__ == '__main__':

    from b3.fake import fakeConsole, superadmin

    fakeConsole.gameName = 'cod4'
    p = GgcstreamPlugin(fakeConsole)
    p.onStartup()
    
    def testCommand():
        superadmin.connects(0)
        superadmin.says('!ggcstream')

    def testQuery(ip, port):
        print('_'*20)
        print("%s:%s" % (ip, port))
        jsondata = p._queryGGCStreamService(ip, port)
        print(jsondata)
        if 'heartbeat' in jsondata and jsondata['heartbeat']:
            print(time.time() - jsondata['heartbeat'])

    #testCommand()
    testQuery("213.163.68.23", 25700)
    time.sleep(30)
