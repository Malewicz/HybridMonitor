# -*- coding: utf-8 -*-
"""
PickoffMonitor.py

part of the Hybrid Parameter Monitor by Juan Bohorquez
based on similar code from the CsPy interface written by Donlad Booth

handles reading analog data from an NI-DAQmx interface


Created on Wed Jun 06 12:22:07 2018
"""
__author__ = 'Juan Bohorquez'

import logging
logger = logging.getLogger(__name__)

from cs_errors import PauseError
from ctypes import *
import numpy



class NIDAQmxAI():
    version = '2016.12.21'

    allow_evaluation = True
    enable = False
    DAQmx_Val_RSE = 10083
    DAQmx_Val_NRSE = 10078
    DAQmx_Val_Diff = 10106
    DAQmx_Val_PseudoDiff = 12529
    DAQmx_Val_Volts = 10348
    DAQmx_Val_Rising = 10280
    DAQmx_Val_Falling = 10171
    DAQmx_Val_FiniteSamps = 10178
    DAQmx_Val_GroupByChannel = 0
    DAQmx_Val_GroupByScanNumber = 1
    DAQmx_Val_ChanPerLine = 0
    applyFormula = False

    def __init__(self,channelMap):
        self.DeviceName = "Dev1"
        self.samples_per_measurement = 2
        self.sample_rate = 1000
        self.triggerSource = '/Dev1/PFI0'
        self.triggerEdge = 'Rising'
        self.formula = [lambda v : 1.016*v-2.1,
                        lambda v : 0.935*v+17.2,
                        lambda v : 0.422-0.001,
                        lambda v : 25.45+950,
                        lambda v : 0.685+0.00556,
                        lambda v : 2.008+28.4]
        
        self.nidaq = windll.nicaiu
        self.DAQmx_Val_Cfg_Default = c_long(-1)
        self.taskHandle = c_ulong(0)
        self.channelMap = channelMap
        self.channellist = ['ai0','ai1','ai2','ai3','ai4','ai5']
        self.mychans = self.channelString()
        
    def channelString(self):
        mychans = ""
        for i,chan in enumerate(self.channellist.values()):
            if i<len(self.channellist)-1:
                mychans+=self.DeviceName.value+"/"+chan+", "
            else:
                mychans+=self.DeviceName.value+"/"+chan
                
        return mychans

    def CHK(self,err,func):
        if err<0:
            buf_size = 1000
            buf = create_string_buffer('\000'*buf_size)
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            logger.error('nidaq call %s failed with error %d: %s'%(func,err,repr(buf.value)))
            raise PauseError


    def prepareTask(self,trig = True):
        
        if self.taskHandle.value != 0:
            self.nidaq.DAQmxStopTask(self.taskHandle)
            self.nidaq.DAQmxClearTask(self.taskHandle)
        #Open the measurement task
        self.CHK(self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)),"CreateTask")
        
        
        #initialize data location
        self.data = numpy.zeros((self.samples_per_measurement.value*len(self.channellist),),dtype=numpy.float64)
        
        #open the input voltage channels
        self.CHK(self.nidaq.DAQmxCreatAIVoltageChan(self.taskHandle,
                                                    c_char_p(self.mychans),
                                                    "",
                                                    self.DAQmx_Val_RSE,
                                                    c_double(-5.0),
                                                    c_double(5.0),
                                                    self.DAQmx_Val_Volts),"CreateAIVoltageChan")
        
        #configure the timing
        self.CHK(self.nidaq.DAQmxCfgSampClkTiming(self.taskHandle,
                                                  "",
                                                  c_double(self.sample_rate.value),
                                                  self.DAQmx_Val_Rising,
                                                  self.DAQmx_Val_FiniteSamps,
                                                  c_uint64(self.samples_per_measurement.value)),"CfgSampClkTiming")
        
        if trig :
            self.CHK(self.nidaq.DAQmxCfgDigEdgeStartTrig(self.taskHandle,
                                                        c_char_p(self.triggerSource),
                                                        c_int32(self.DAQmx_Val_Rising)),"CfgDigEdgeStartTrig_Rising")
            
        self.CHK(self.nidaq.DAQmxStartTask(self.taskHandle),"StartTask")
        
        return
    
    def get_powers(self) :
        self.prepareTask(trig = True)
        read = c_int32()
        self.CHK(self.nidaq.DAQmxReadAnalogF64(self.taskHandle,
                                       self.samples_per_measurement.value,
                                       c_double(10.0),
                                       self.DAQmx_Val_GroupByScanNumber,
                                       self.data.ctypes.data,
                                       len(self.data),
                                       byref(read),None),"ReadAnalogF64")
        if self.nidaq.DAQmxWaitUntilTaskDone(self.taskHandle, c_double(4.0)) < 0:
            read = prepareTask(trig = False)
        self.nidaq.DAQmxStopTask(self.taskHandle)
        self.nidaq.DAQmxClearTask(self.taskHandle)
        powers_usort = {}
        for i,chan in enumerate(self.channellist):
            powers_usort.update({chan:func[i](self.data[i])})
        powers = {}
        for key,value in self.channelMap :
            powers.update({key:powers_usort[value]})
        return powers


