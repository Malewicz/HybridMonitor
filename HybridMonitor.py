# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
"""
@Author: Juan Bohorquez
Based on code by Matt Ebert

This class continuously logs data from different sources within hybrid to the 
Origin data server.
"""
import os
import time
import numpy as np
import sys
import Channel
import PicosMonitor
import NIDAQMonitor

'''
# TODO :
    [ ] 1. Refactor
    [ ] 2. Implement and import the magSensor class
    [ ] 3. Determine failure conditions throughout and add corresponding ifs/trys
    [ ] 4. Fix NIDAQMonitor.py to work in general for the NI DAQmx with any given set of inputs
    [ ] 5. Make separate file setup for channel classes
    [ ] 6. Make Device Monitor classes work with config files
'''


def close_all(channel_list):
    """
    closes all the channels in the argument.
    Arguments:
        channels -- array of channels
    """
    status = np.empty(len(channels))
    for i, chan in enumerate(channel_list):
        print "closing channel : " + chan.name
        status[i] = chan.hang()
    return status


measurementPeriod = 30  # s

t0 = time.clock()
# we must first find ourselves
print 'finding ourselves'
fullBinPath = os.path.abspath(os.getcwd())
print fullBinPath
fullBasePath = os.path.dirname(fullBinPath)
print fullBasePath
fullLibPath = os.path.join(fullBasePath, "origin\\origin\\lib")
fullCfgPath = os.path.join(fullBasePath, "origin\\origin\\config")
sys.path.append(fullLibPath)

print 'getting origin'
from origin.client import server
from origin import current_time, TIMESTAMP

print 'initializing picos'
# initialize the picos monitor
tempChannels = {"Chamber": 1, "Coils": 2, "Near_Terminal": 3}
picosDLLPath = "C:\Program Files\Pico Technology\SDK\lib"
picos = PicosMonitor.TC08USB(tempChannels, dll_path=picosDLLPath)

print 'initializing pickoff monitor'
# initialize the pickoff monitor
I2VChannels = {"X1": 'ai4',
               "X2": 'ai2',
               "Y1": 'ai0',
               "Y2": 'ai1',
               "Z1": 'ai3',
               "Z2": 'ai5'}
# pickoff conversions
I2VConversion = {"X1": lambda v: 0.685*v+0.00556,
                 "X2": lambda v: 0.422*v-0.001,
                 "Y1": lambda v: 1.016*v-0.0021,
                 "Y2": lambda v: 0.935*v+0.0172,
                 "Z1": lambda v: 0.447*v+0.009,
                 "Z2": lambda v: 2.008*v+0.0284}

I2V = NIDAQMonitor.NIDAQmxAI(I2VChannels, conversion=I2VConversion)

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
# open the channels
channels = []
channels.append(Channel("Temp", "float", serv, tempChannels, picos))
channels.append(Channel("Beam_Balances", "float", serv, I2VChannels, I2V))
#    channels.append(magChannel("B","float",serv,["X,Y,Z"]))


# This might need to be more complicated, but you get the gist. Keep sending records forever
time.sleep(10)

print 'begin communication'
err = 0
# TODO : Make timing consistent despite wait blocks in monitor classes
# TODO : Write data to channels in multiple threads once the number of channels gets large
while True:
    try:
        # t1 = time.clock()
        for channel in channels:
            print "sending " + channel.name
            print "Measured :" + repr(channel.measure())
            ts = current_time(config)
            data = channel.data
            data.update({TIMESTAMP: ts})
            try:
                channel.connection.send(**channel.data)
            except Exception:
                close_all(channels)
                raise Exception
            print(data)
            # interrupt this with a keystroke and hang connection
        if err == 1:
            break
        time.sleep(measurementPeriod)
        # FOR TIMING:
        # t2 = time.clock()
        # deltaT = t2 - t1
        # time.sleep(measurementPeriod - deltaT)

    except KeyboardInterrupt:
        close_all(channels)
        raise KeyboardInterrupt
        break
