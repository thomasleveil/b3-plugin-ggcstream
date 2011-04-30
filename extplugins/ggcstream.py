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


__version__ = '0.2'
__author__ = 'Courgette'


import time, threading
import b3.plugin
from b3.events import EVT_UNKNOWN




SUPPORTED_PARSERS = {
                     'bfbc2': 'bc2',
                     'moh': 'moh',
                     'cod': 'cod',
                     'cod2': 'cod2',
                     'cod4': 'cod4',
                     'cod5': 'codww',
                     'et': 'et',
                     'etpro': 'et'}

FROSTBITE_GAMES = ('bfbc2', 'moh')

class UnsupportedGameError(Exception):
    pass

#--------------------------------------------------------------------------------------------------
class GgcstreamPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _adminPlugin = None
    _frostbite_async_pb_msg = []

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
        
        threading.Timer(10.0, self._install_GGCStream).start()

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
        install the GGC Stream service
        """
        try:
            self._install_GGCStream(client=client)
            client.message("GGC Stream setup on this server")
        except UnsupportedGameError:
            client.message("this game is not supported")


    def _install_GGCStream(self, client=None):
        try:
            self._do_uconadd(gamecode=SUPPORTED_PARSERS[self.console.gameName], client=client)
        except KeyError, e:
            raise UnsupportedGameError(e)


    def _do_uconadd(self, gamecode=None, client=None):
        # test presence of pbucon.use
        data = self._rconMethod("pb_sv_uconadd")
        if 'pbucon.use' in data:
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
                time.sleep(.2)
        return None


    def onPunkbusterEvent(self, data):
        self.debug("punbuster : %s", data)
        self._frostbite_async_pb_msg.append(data)



if __name__ == '__main__':

    from b3.fake import fakeConsole, superadmin

    def testCommand():
        p = GgcstreamPlugin(fakeConsole)
        p.onStartup()
        superadmin.connects(0)
        superadmin.says('!ggcstream')

    fakeConsole.gameName = 'cod4'
    
    testCommand()
    
    time.sleep(60)
