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

#from cs_errors import PauseError
from ctypes import *
import numpy
import time



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
        self.DeviceName = "PXI2Slot6"
        self.samples_per_measurement = 2
        self.sample_rate = 1000
        self.triggerSource = '/PXI2Slot6/PFI0'
        self.triggerEdge = 'Rising'
        self.formula = [lambda v : 1.016*v-.0021,
                        lambda v : 0.935*v+.0172,
                        lambda v : 0.422*v-0.001,
                        lambda v : 0.447*v+.0009,
                        lambda v : 0.685*v+0.00556,
                        lambda v : 2.008*v+.0284]
        
        self.nidaq = windll.nicaiu
        self.DAQmx_Val_Cfg_Default = c_long(-1)
        self.taskHandle = c_ulong(0)
        self.channelMap = channelMap
        self.channellist = ['ai0','ai1','ai2','ai3','ai4','ai5']
        self.mychans = self.channelString()
        self.prepareTask()
        
    def channelString(self):
        mychans = ""
        for i,chan in enumerate(self.channellist):
            if i<len(self.channellist)-1:
                mychans+=self.DeviceName+"/"+chan+", "
            else:
                mychans+=self.DeviceName+"/"+chan
                
        return mychans

    def CHK(self,err,func):
        if err<0:
            buf_size = 1000
            buf = create_string_buffer('\000'*buf_size)
            bufV_size = 2000
            bufV = create_string_buffer('\000'*bufV_size)
            self.nidaq.DAQmxGetErrorString(err,byref(buf),buf_size)
            self.nidaq.DAQmxGetExtendedErrorInfo(byref(bufV),bufV_size)
            print 'nidaq call %s failed with error %d: %s'%(func,err,repr(buf.value))
            print 'nidaq call %s failed with verbose error %d: %s'%(func,err,repr(bufV.value))
            raise ValueError


    def prepareTask(self,trig = True):
        
        try :
            if self.taskHandle.value != 0:
                self.nidaq.DAQmxStopTask(self.taskHandle)
                self.nidaq.DAQmxClearTask(self.taskHandle)
                self.taskHandle = c_ulong(0)
                time.sleep(2)   
            #Open the measurement task

            self.CHK(self.nidaq.DAQmxCreateTask("",byref(self.taskHandle)),"CreateTask")
            
            print "Task Handle: {}".format(self.taskHandle.value)
            
            #initialize data location
            self.data = numpy.zeros((self.samples_per_measurement*len(self.channellist),),dtype=numpy.float64)
            
            #open the input voltage channels
            self.CHK(self.nidaq.DAQmxCreateAIVoltageChan(self.taskHandle,
                                                        c_char_p(self.mychans),
                                                        "",
                                                        self.DAQmx_Val_RSE,
                                                        c_double(-5.0),
                                                        c_double(5.0),
                                                        self.DAQmx_Val_Volts,
                                                        None),"CreateAIVoltageChan")
            
            #configure the timing
            self.CHK(self.nidaq.DAQmxCfgSampClkTiming(self.taskHandle,
                                                      "",
                                                      c_double(self.sample_rate),
                                                      self.DAQmx_Val_Rising,
                                                      self.DAQmx_Val_FiniteSamps,
                                                      c_uint64(self.samples_per_measurement)),"CfgSampClkTiming")
            
            if trig :
                self.CHK(self.nidaq.DAQmxCfgDigEdgeStartTrig(self.taskHandle,
                                                            c_char_p(self.triggerSource),
                                                            c_int32(self.DAQmx_Val_Rising)),"CfgDigEdgeStartTrig_Rising")
                
            self.CHK(self.nidaq.DAQmxStartTask(self.taskHandle),"StartTask")
            
            return
        except KeyboardInterrupt as e :
            self.close_task()
            raise KeyboardInterrupt
    
    def get_powers(self) :
        try :
            read = c_int32()
            print "reading out in triggered mode"
            self.nidaq.DAQmxReadAnalogF64(self.taskHandle,
                                           self.samples_per_measurement,
                                           c_double(10.0),
                                           self.DAQmx_Val_GroupByScanNumber,
                                           self.data.ctypes.data,
                                           len(self.data),
                                           byref(read),None)
            if self.nidaq.DAQmxWaitUntilTaskDone(self.taskHandle, c_double(4.0)) < 0:
                print "reading out in auto mode"
                self.nidaq.DAQmxStopTask(self.taskHandle)
                self.nidaq.DAQmxDisableStartTrig(self.taskHandle)
                self.nidaq.DAQmxStartTask(self.taskHandle)
                self.CHK(self.nidaq.DAQmxReadAnalogF64(self.taskHandle,
                                            self.samples_per_measurement,
                                            c_double(10.0),
                                            self.DAQmx_Val_GroupByScanNumber,
                                            self.data.ctypes.data,
                                            len(self.data),
                                            byref(read),None),"ReadAnalogF64")
                if self.nidaq.DAQmxWaitUntilTaskDone(self.taskHandle, c_double(4.0)) < 0:
                    print "Something went wrong."
                    raise ValueError
      
            self.nidaq.DAQmxStopTask(self.taskHandle)
            self.CHK(self.nidaq.DAQmxCfgDigEdgeStartTrig(self.taskHandle,
                                                            c_char_p(self.triggerSource),
                                                            c_int32(self.DAQmx_Val_Rising)),"CfgDigEdgeStartTrig_Rising")
            self.CHK(self.nidaq.DAQmxStartTask(self.taskHandle),"Restarting triggered task")
            powers_usort = {}
            for i,chan in enumerate(self.channellist):
                powers_usort.update({chan:self.formula[i](self.data[i])})
            print powers_usort
            
            powers = {}
            print self.channelMap
            for key,value in self.channelMap.iteritems() :
                print key,value
                powers.update({key:powers_usort[value]})
            return powers
        except KeyboardInterrupt as e :
            self.close_task()
            raise KeyboardInterrupt
            
    def close_task(self) :
        print 'Closing DAQmx task'
        self.CHK(self.nidaq.DAQmxStopTask(self.taskHandle),"Stopping Task")
        self.CHK(self.nidaq.DAQmxClearTask(self.taskHandle),"Clearing Task")