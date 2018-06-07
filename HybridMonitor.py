# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
"""
@Author: Juan Bohorquez
Based on code by Matt Ebert

This class continuously logs data from different sources within hybrid to the 
Origin data server.
"""

'''
TO DO before trying this out:
    1. Implement and import the picos class
    2. Implement and import the magSensor class
    3. determine failure conditions throughout and add corresponding ifs/trys
    4. implement hang() function in channel class
'''

#!/usr/bin/env python
import os
import random
import time
import zmq
import json
import numpy as np
import requests
import sys
import PicosMonitor

class channel(object):
    """
    A base class for all channels which connect to the server.
    """
    def __init__(self, name, dataType,server,dataNames):
        """
        Arguments:
            name -- the name of the channel to be used
            dataType -- the data type to be written to the server.
                for options see ../lib/origin/origin_data_types.py
                or origin-test-datatypes-binary
            server -- the server class representing connection to Origin
            dataNames -- the names of the different data sets to be sent over
                this channel
        """
        self.name = "Hybrid_" + name
        self.dataType = dataType
        self.serv = server
        self.connection = self.connect()
        self.records = {}
        self.dataNames = dataNames
        for dataName in dataNames:
            self.records.update({dataName:dataType})
        self.data = {}
        
    def connect(self) :
        """
        lets the server know we going to be sending this type of data
        """
        chan = self.serv.registerStream(
                stream = self.name, 
                records = self.records)
        return chan
    def measure(self) :
        """
        Overwrite this funciton with something that returns your data
        should return an list with the same dimensions as dataNames.
        """
        self.data = dict(zip(
                self.dataNames,
                np.random(1,len(self.dataNames)).tolist()
                ))
        return self.data
    def hang(self):
        """
        Closes connection with the server. Returns status/error
        INCOMPLETE
        """
        return 0
        
class tempChannel(channel):
    """
    Class to deal with a channel opened to monitor the temperature
    """
    def __init__(self, name, dataType,server,dataNames,picos):
        """
        Arguments
            picos -- object representing connection to picos TC-08 temperature
                monitor
        """
        super(tempChannel,self).__init__(self, name, dataType,server)
        self.picos = picos
    def measure(self) :
        """
        Determines the temperatures measured at different locations in hybrid.
        saves them to data as a dictionary mapped to datanames (make sure you
        get the order right)
        """
        self.data = dict(zip(
                self.dataNames,
                self.picos.get_temp()
                ))
        return self.data

    
class magChannel(channel):
    """
    Class to deal with the magnetic field monitor near the science chamber
    """
    def __init__(self, name, dataType,server,dataNames,magSensor):
        """
        Arguments
            magSensor -- represents connection to magnetic field sensor (Not 
            yet installed)
        """
        super(tempChannel,self).__init__(self, name, dataType,server)
        self.magSensor = magSensor
    def measure(self):
        """
        Determines the magnetic field measured by the sensor, saves it to data
        as a dictionary mapped to datanames (make sure you get the order right)
        """
        self.data = dict(zip(
                self.dataNames,
                self.magSensor.getField()
                ))
        return self.data
    
def main () :
    #we must first find ourselves
    fullBinPath  = os.path.abspath(os.getcwd() + "/" + sys.argv[0])
    fullBasePath = os.path.dirname(os.path.dirname(fullBinPath))
    fullLibPath  = os.path.join(fullBasePath, "lib")
    fullCfgPath  = os.path.join(fullBasePath, "config")
    sys.path.append(fullLibPath)
    
    from origin.client import server
    from origin import current_time, TIMESTAMP
    
    #initialize the picos 
    tempChannels = {"Chamber" : 1,"Coils" : 2}
    picosDLLPath = "C:\Program Files\Pico Technology\SDK\lib"
    picos = PicosMonitor.TC08USB(dll_path = picosDLLPath)
    picos.start_unit(tempChannels.values())
    
    if len(sys.argv) > 1:
      if sys.argv[1] == 'test':
        configfile = os.path.join(fullCfgPath, "origin-server-test.cfg")
      else:
        configfile = os.path.join(fullCfgPath, sys.argv[1])
    else:
      configfile = os.path.join(fullCfgPath, "origin-server.cfg")
    
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read(configfile)
    
    # something that represents the connection to the server
    serv = server(config)
    #open the channels
    channels = []
    channels.append(tempChannel("Temp","float",serv,tempChannels.keys(),picos))
#    channels.append(magChannel("B","float",serv,["X,Y,Z"]))
    
    
    # This might need to be more complicated, but you get the gist. Keep sending records forever
    time.sleep(5)
    
    while True:
        for channel in channels :
            print "sending " + channel.name
            channel.measure()
            ts = current_time(config)
            data = channel.data.update({TIMESTAMP:ts})
            channel.connection.send(data)
            print(data)
            time.sleep(1)
            #if there's an error break out of both loops and close the connections