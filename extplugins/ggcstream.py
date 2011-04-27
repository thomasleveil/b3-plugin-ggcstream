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


__version__ = '0.1'
__author__ = 'Courgette'


import b3.plugin
import time, threading



SUPPORTED_PARSERS = ['bfbc2', 'moh', 'cod', 'cod2', 'cod4', 'cod5', 'et', 'etpro']

class UnsupportedGameError(Exception):
    pass

#--------------------------------------------------------------------------------------------------
class GgcstreamPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _adminPlugin = None

    def onStartup(self):
        if self.console.gameName not in SUPPORTED_PARSERS:
            self.error("This game is not supported by this plugin")
            self.disable()
            return

        # get the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        self._adminPlugin.registerCommand(self, "ggcstream", 100, self.cmd_ggcstream)
        
        threading.Timer(10.0, self._install_GGCStream).start()
        

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
        gamecode = None
        if self.console.gameName == 'cod4':
            gamecode = 'cod4'
        #elif self.console.gameName == 'bfbc2':
        #    gamecode = 'bc2'
        else:
            raise UnsupportedGameError()
        self._do_uconadd(gamecode=gamecode, client=client)


    def _do_uconadd(self, gamecode=None, client=None):
        if gamecode is None:
            return
        # test presence of pbucon.use
        data = self.console.write("pb_sv_uconadd")
        if 'pbucon.use' in data:
            # no pbucon.use file : we need to create it and restart pb
            if client: client.message("creating pbucon.use file")
            self.info(self.console.write("pb_sv_writecfg pbucon.use"))
            self.info(self.console.write("pb_sv_restart"))
            if client: client.message("restarting punkbuster, please wait...") 
            time.sleep(20)
        if client: client.message("adding GGC Stream to punkbuster config")
        self.info(self.console.write("pb_sv_USessionLimit 9"))
        self.info(self.console.write("pb_sv_uconadd 1 85.214.107.154 ggc_85.214.107.154 %s" % gamecode))
        self.info(self.console.write("pb_sv_uconadd 1 85.214.107.155 ggc_85.214.107.155 %s" % gamecode))
        self.info(self.console.write("pb_sv_uconadd 1 85.214.107.156 ggc_85.214.107.156 %s" % gamecode))
        if client: client.message("saving punkbuster config")
        self.info(self.console.write("pb_sv_writecfg"))


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
