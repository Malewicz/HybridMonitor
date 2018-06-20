"""
Created on Wed Mar 07 17:09:54 2018

@Author: Juan Bohorquez
Based on code by scls19fr from picotech tech support forum
Currently only supports one device

Class to control communication with the Picos TC-08 temperature monitor
"""
#!/usr/bin/env python
# coding: utf8

import ctypes
from ctypes import *
import numpy as np
import os

class TC08USB(object):
    TC_ERRORS = {
        0 : 'OK',
        1 : 'OS_NOT_SUPPORTED',
        2 : 'NO_CHANNELS_SET',
        3 : 'INVALID_PARAMETER',
        4 : 'VARIANT_NOT_SUPPORTED',
        5 : 'INCORRECT_MODE',
        6 : 'ENUMERATION_INCOMPLETE',
        7 : 'NOT_RESPONDING',
        8 : 'FW_FAIL',
        9 : 'CONFIG_FAIL',
        10 : 'NOT_FOUND',
        11 : 'THREAD_FAIL',
        12 : 'PIPE_INFO_FAIL',
        13 : 'NOT_CALIBRATED',
        14 : 'PICOPP_TOO_OLD',
        15 : 'COMMUNICATION'
    }
    
    TC_UNITS = {
        'CENTIGRADE' : 0,
        'FAHRENHEIT' : 1,
        'KELVIN' : 2,
        'RANKINE' : 3
    }
    def __init__(self, dll_path=""):
        """
        Arguments:
            dll_path -- string indicating the location of the dll to be loaded        
        """
        dll_filename = os.path.join(dll_path, 'usbtc08.dll')
        self._dll = ctypes.windll.LoadLibrary(dll_filename)
        
        self._handle = None # handle for device
        
        self._temp = np.zeros( (9,), dtype=np.float32)
        self._overflow_flags = np.zeros( (1,), dtype=np.int16)
        
        self._units = self.TC_UNITS['CENTIGRADE']
        
    def open_unit(self):
        self._handle = self._dll.usb_tc08_open_unit()
        return(self._handle)
        
    def set_mains(self, value=60):
        return(self._dll.usb_tc08_set_mains(self._handle, c_int16(value)))
        
    def set_channel(self, channel, tc_type):
        return(self._dll.usb_tc08_set_channel(self._handle, channel, c_char(tc_type) ) )

    def get_single(self):
        return(self._dll.usb_tc08_get_single(self._handle, self._temp.ctypes.data, self._overflow_flags.ctypes.data, self._units))

    def close_unit(self):
        return(self._dll.usb_tc08_close_unit(self._handle))
        
    def close_other_unit(self,otherHandle)    :
        return(self._dll.usb_tc08_close_unit(otherHandle))
        
    def get_last_error(self):
        return(self._dll.usb_tc08_get_last_error(self._handle))
        
    def __getitem__(self, channel):
        return(self._temp[channel])
        
    def print_error(self,message = ''):
        error = self.get_last_error()
        print str(self.close_unit())
        message += self.TC_ERRORS[error]
        print message
        return error
    def start_unit(self,channels,mains = 60,tc_type = 'k'):
        '''
        Initializes the TC-08 unit as desired
        Returns 0 if there are no errors, returns error code otherwise
        Arguments:
            channels -- array of ints indicating channels to be opened (1-8)
            mains -- frequency for mains rejection, 50 of 60 Hz
            tc_type -- char indicating the thermocouple type being used
        '''
        
        self.chanList = channels
        
        if self.open_unit() < 1:
            i = 0
            #a unit can remain open and have an active handle which is not self.handle
            #this prevents opening that unit again. This while loop should clean
            #that up
            while self._handle == 0 :
                i += 1
                if i > 30 :
                    return self.print_error('No units detected :')
                if self.close_other_unit(i) == 1 :
                    self.open_unit()
            if self._handle < 0 :
                return self.printError('Error opeining unit : ')
                
        if self.set_mains(mains) == 0 :
            return self.printError('Error setting mains rejection : ')
        
        for channel in channels.values() :
            if self.set_channel(channel,tc_type) < 1 :
                return self.printError('Error setting channel ' + str(channel) + ' : ')
            
        return 0
    def get_temp(self):
        """
        Queries the Picos USB TC08 to measure the temperatures then generates a
        dictionary of temperature stream names to their value
        Returns:
            -data: a dictionary with keys indicating what temperature is being measured
                and values with the temperature in Centigrade. Types : {String : np.float_32}
        """
        self.get_single()
        data = {}
        for key,value in self.chanList.iteritems():
            data.update({key:self._temp[value]})
        return data