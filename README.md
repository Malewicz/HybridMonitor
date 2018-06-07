# HybridMonitor
Parameter Monitoring Program used in the Hybrid Experiment

# Installation:
1. clone this repo onto your machine.  
2. Replace the link labeled Origin with a symbolic link to your origin repo  
   -If your filepath looks like GitRepos/Origin/origin/ set the link to the innermost origin folder  
3. Run python HybridMonitor.py

# Programming guide:
This program consists of the HybridMonitor.py file and Device Monitor python files which take care of communication with a given measurement device.

* The HybridMonitor.py uses channel classes based on a parent channel class defined within the file. These classes take care of the communication with the Device Monitor files as well as writting to the server.   
* Currently custom channel classes are written for each device, this provides some flexibility in how Device Monitor classes are written but may be cumbersome. 
* Besides defining these channel classes HybridMonitor.py manages some of the origin server and instructs the channel classes when to write to the server.
* The only way to turn off the data stream (that I've implemented) is with a KeyboardInterupt, it is important that your each channel has a hang function, this function should close the connection to the server and clear any connections to the device, if that isn't done automatically.  
* Device Monitor classes (such as PicosMonitor.py) need to interact with a given device. They only requirement for these classes is that they have some callable function which returns a dictionary or list of data.
* The corresponding channel class should set channel.data to a dictionary of data and dataNames, this is what is sent to the server.

# Current Device Monitor Files: 

## Picos Temperature Monitor (PicosMonitor.py)
* Interfaces with the Picos TC-88 Temperature Monitor
  * Thermocouple logger
* Driver Documentation: See "Thermocouple logger Programmer's guide.pdf"

## I2V Pickoff Monitor (PickoffMonitor.py)
* Interfaces with the NI DAQmx usb connected A/DC
* Specifically written for the MOT beam pickoffs currently
  * Can be modified to work with the NI DAQmx in for general purpose use as and A/DC
* Driver Documentation: http://zone.ni.com/reference/en-XX/help/370471AA-01/
  
# Device Monitor Files to be built :

## MagSensor
* Should Interface with an AD/C connected to the Magnetic Field Sensor
* Hopefully will use same NI DAQmx as the I2V Pickoff Monitor
