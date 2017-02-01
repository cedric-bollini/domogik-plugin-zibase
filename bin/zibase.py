#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

ZiBase management

Implements
==========

- ZiBaseMain

@author: Cedric BOLLINI <cb.dev@sfr.fr>
@copyright: (C) 2007-2012 Domogik project
@license: GPL(v3)
"""

from domogik.xpl.common.xplconnector import Listener, XplTimer
from domogik.xpl.common.plugin import XplPlugin
from domogik.xpl.common.xplmessage import XplMessage
#from domogik.xpl.common.queryconfig import Query
from domogik_packages.plugin_zibase.lib.zibase import APIZiBase, get_ip_address, ServerZiBase
import threading
import traceback
import time


class ZiBaseMain(XplPlugin):
    '''Manage ZiBase
    '''	
    def __init__(self):
        """ Create lister and launch bg listening
        """
        XplPlugin.__init__(self, name = 'zibase')

	# check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

	# check if the plugin is configured. If not, this will stop the plugin and log an error
        if not self.check_configured():
            return

        self.address = self.get_config('ip')
        self.inter = self.get_config('interface')
        self.port = int(self.get_config('port'))
        self.valvar=self.get_config('envar')
        self.interv=int(self.get_config('interv'))

	# get the devices list
        # for this plugin, if no devices are created we won't be able to use devices.
        # but.... if we stop the plugin right now, we won't be able to detect existing device and send events about them
        # so we don't stop the plugin if no devices are created
        self.devices = self.get_device_list(quit_if_no_device = False)

        #self._config = Query(self.myxpl, self.log)



        self.log.info("Creating listener for ZiBase")

        Listener(self.zibase_command, self.myxpl, {'schema': 'zibase.basic',
                'xpltype': 'xpl-cmnd'})
        
        try:
            self.ip_host=get_ip_address(str(self.inter))
            self.log.debug("Adress IP Host=%s" % (self.ip_host))
        except:
            self.log.error("IP Host not found=%s" % (traceback.format_exc()))
            self.force_leave()
            return

        try:
            self.api = APIZiBase(self.log,self.address)
        except:
            self.log.error("API ZiBase error=%s" % (traceback.format_exc()))
            self.force_leave()
            return

        try:
            self.th=ServerZiBase(self.log,self.ip_host,self.port,self.myxpl)
            self.th.start()
        except:
            self.log.error("Server ZiBase error=%s" % (traceback.format_exc()))
            self.force_leave()

        try:
            self.api.Connect(self.ip_host,self.port)
        except:
            self.log.error("Connection ZiBase error=%s" % (traceback.format_exc()))
            self.force_leave()

        if self.valvar :
            try:
                self.log.info("Start reading internal variables")
                var_read=XplTimer(self.interv,self.zibase_read_var,self.myxpl)
                var_read.start()
            except:
                self.log.error("reading internal variables error")
		self.force_leave()
                return

        #self.add_stop_cb(self.stop)
        #self.enable_hbeat()
	self.ready()

        self.log.info("Plugin ready :)")
        
    def zibase_command(self, message):
        """ Call zibase lib function in function of given xpl message
            @param message : xpl message
        """
        commands = {
            'off': 0,
            'on': 1,
            'preset-dim' : 2,
        }
        protocols = {
            'PRESET': 0,
            'VISONIC433' : 1,
            'VISONIC868' : 2,
            'CHACON' : 3,
            'DOMIA' : 4,
            'X10' : 5,
            'ZWAVE' : 6,
            'RFS10' : 7,
            'XDD433AL' : 8,
            'XDD868AL' : 9,
            'XDD868INSH' : 10,
            'XDD868PILOT' : 11,
            'XDD868BOAC' : 12,
        }

        cmd = None
        dev = None
        protocol = None
        preset_dim = 0
        
        if 'command' in message.data:
            cmd = message.data['command']
        if 'device' in message.data:
            chaine=message.data['device'].split(':')
            try:
                dev = chaine[0].upper()
                protocol=chaine[1].upper()
            except:
                self.log.error("Syntax device not valid")
        if 'preset-dim' in message.data:
            preset_dim=message.data['preset-dim']

        self.log.debug(message.data)
        if protocol == None :
            self.log.warning("Protocol Device not specified !!!!")
            return
        else:
            self.log.debug("%s received : device = %s protocol = %s number protocol=%s preset=%s" % (cmd, dev, protocol, protocols[protocol],str(preset_dim)))
            try:
                self.api.sendCommand(dev, commands[cmd], protocols[protocol],int(preset_dim))
                time.sleep(1)
                self.th.send_xpl_cmd(message.data['device'], cmd, preset_dim)
            except:
                self.log.error("Sendcommand error")
                return





    def stop(self):
        self.log.debug("Stop plugin in progress...")
        self.var_read.stop()
        self.api.Disconnect(self.ip_host,self.port)
        self.th.stop()
        return
    
    def zibase_read_var(self):
        try:
            datas=self.api.getVariables()
            if datas!=None:
                for data in datas:
                    elmt=data.split(':')
                    stats=['sta:' + elmt[1]]
                    self.th.send_xpl_sensor(stats,elmt[0],'xpl-stat')
        except:
            self.log.error("Read var error=%s" % (traceback.format_exc()))
                        



if __name__ == "__main__":
    ZiBaseMain()
