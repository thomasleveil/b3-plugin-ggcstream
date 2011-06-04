GGC Stream plugin for Big Brother Bot (www.bigbrotherbot.net)
=============================================================

By Courgette


Description
-----------

This plugin installs GGC Stream on your game server. See http://ggc-stream.com

Requires PunkBuster
Requires an account on http://ggc-stream.com

When you start B3, this plugin will check if your server is streaming to GGC Stream.
If not it will set up your punkbuster config for GGC Stream.
You still need to create an account and register your server at http://ggc-stream.com

In game, you can use the !ggcstream command to check if GGC Stream is receiving 
your stream and if not it will try to set it up.


Installation
------------

 * copy ggcstream.py into b3/extplugins
 * update your main b3 config file with :

<plugin name="ggcstream" />



Changelog
---------

2011-04-27 - 0.1 
* first release. cod4 support

2011-04-29 - 0.2
* add support for frostbite games bfbc2 and moh (tested)
* add suuport for games cod, cod2, cod5, et and etpro (untested)

2011-06-04 - 1.0
* B3 will only install the streaming service if GGC Stream reports an error.
* the !ggcstream commands now ask the GGC server if our server is correctly
  streaming


Support
-------

