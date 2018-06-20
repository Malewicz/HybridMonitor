# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
"""
@Author: Juan Bohorquez
Based on code by Matt Ebert

This class continuously logs data from different sources within hybrid to the 
Origin data server.
"""

'''
TO DO:
    [ ] 1. Implement a GUI in pyqt5
    [ ] 2. Implement and import the magSensor class
    [ ] 3. Determine failure conditions throughout and add corresponding ifs/trys
    [ ] 4. Fix PickoffMonitor.py to work in general for the NI DAQmx with any given set of inputs
    [ ] 5. Make separate file setup for channel classes
    [ ] 6. Make Device Monitor classes work with config files
'''

#!/usr/bin/env python
import os
import time
import numpy as np
import sys
import PicosMonitor
import PickoffMonitor
import signal



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
        self.records = {}
        self.dataNames = dataNames
        for dataName in dataNames:
            self.records.update({dataName:dataType})
        self.connection = self.connect()
        self.data = {}
        
    def connect(self) :
        """
        lets the server know we going to be sending this type of data
        """
        print self.records
        chan = self.serv.registerStream(
                stream = self.name, 
                records = self.records,
                timeout = 30*1000)
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
        """
        self.connection.close()
        
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
        super(tempChannel,self).__init__(name, dataType,server,dataNames)
        self.picos = picos
    def measure(self) :
        """
        Determines the temperatures measured at different locations in hybrid.
        saves them to data as a dictionary mapped to datanames (make sure you
        get the order right)
        """
        self.data = self.picos.get_temp()
        return self.data

class I2VChannel(channel):
    """
    Class to deal with analog inputs from the NIDAQmx monitors
    """
    def __init__(self,name,dataType,server,dataNames,I2Vmonitor):
        super(I2VChannel,self).__init__(name,dataType,server,dataNames)
        self.I2Vmonitor = I2Vmonitor
    def measure(self):
        """
        Calls the NIDAQ's measurement class, which should return an array of powers organized by the channel mapping
        """
        self.data = self.I2Vmonitor.get_powers()
        return self.data
    def hang(self) :
        """
        Closes the connection with the server. Returns status/error and closes open tasks in DAQmx
        """
        self.I2Vmonitor.close_task()
        self.connection.close()
        
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
        super(tempChannel,self).__init__(name, dataType,server,dataNames)
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


def closeAll (channels):
    """
    closes all the channels in the argument.
    Arguments:
        channels -- array of channels
    """
    for channel in channels:
        print "closing channel : " + channel.name
        channel.hang()
        
measurementPeriod = 30 #s

t0 = time.clock()
#we must first find ourselves
print 'finding ourselves'
fullBinPath  = os.path.abspath(os.getcwd() + "/" + sys.argv[0])
print fullBinPath
fullBasePath = os.path.dirname(fullBinPath)
print fullBasePath
fullLibPath  = os.path.join(fullBasePath, "origin\\lib")
fullCfgPath  = os.path.join(fullBasePath, "origin\\config")
sys.path.append(fullLibPath)

print 'getting origin'
from origin.client import server
from origin import current_time, TIMESTAMP

print 'initializing picos'
#initialize the picos 
tempChannels = {"Chamber" : 1,"Coils" : 2,"Near_Terminal" : 3}
picosDLLPath = "C:\Program Files\Pico Technology\SDK\lib"
picos = PicosMonitor.TC08USB(dll_path = picosDLLPath)
print repr(picos.TC_ERRORS[picos.start_unit(tempChannels)])

print 'initializing pickoff monitor'
#initialize the pickoff monitor
I2VChannels = {"X1" : 'ai4',
               "X2" : 'ai2',
               "Y1" : 'ai0',
               "Y2" : 'ai1',
               "Z1" : 'ai3',
               "Z2" : 'ai5'}
I2V = PickoffMonitor.NIDAQmxAI(I2VChannels)


print 'grabbing config file'
if len(sys.argv) > 1:
    if sys.argv[1] == 'test':
        configfile = os.path.join(fullCfgPath, "origin-server-test.cfg")
    else:
        configfile = os.path.join(fullCfgPath, sys.argv[1])
else:
    configfile = os.path.join(fullCfgPath, "origin-server.cfg")

import ConfigParser
config = ConfigParser.ConfigParser()
print configfile
config.read(configfile)

# something that represents the connection to the server
print 'grabbing server'
serv = server(config)
print 'opening channels'
#open the channels
channels = []
channels.append(tempChannel("Temp","float",serv,tempChannels.keys(),picos))
channels.append(I2VChannel("Beam_Balances","float",serv,I2VChannels.keys(),I2V))
#    channels.append(magChannel("B","float",serv,["X,Y,Z"]))


# This might need to be more complicated, but you get the gist. Keep sending records forever
time.sleep(10)

print 'begin communication'
err = 0
#TODO : Make timinig consistent despite wait blocks in monitor classes
#TODO : Write data to channels in multiple threads once the number of channels gets large
while True:
    try:
        #t1 = time.clock()
        for channel in channels :
            print "sending " + channel.name
            print "Measured :" + repr(channel.measure())
            ts = current_time(config)
            data = channel.data
            data.update({TIMESTAMP:ts})
            try:
                channel.connection.send(**channel.data)
            except:
                closeAll(channels)
                err = 1
                break
            print(data)
            #interrupt this with a keystroke and hang connection
        if err == 1 :
            break
        time.sleep(measurementPeriod)
        #FOR TIMING: 
        #t2 = time.clock()
        #deltaT = t2 - t1
        #time.sleep(measurementPeriod - deltaT)
        
    except KeyboardInterrupt :
        closeAll(channels)
        raise KeyboardInterrupt
        break
