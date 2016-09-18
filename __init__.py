"""
The vlt module aims to bring some useful tool for easy instrument scripts
and control.
It is not aimed to replace the vlt template and script but to provide
to the non-vtl-software expert a way to script VLT instruments.

Main capabilities are:

Process
=======
  You can open a 'process' to send command (based on the msgSend unix command)
  The process object are dynamicaly created from instrument CDT file.
  e.g. (on PIONIER):
  proc = vlt.openProcess("pnoControl")
  proc.help() # give a help on all commands
  proc.help("setup")
      -or-
  print proc.setup.__doc__  # return help on command setup

  vlt.setDefaultProcess("pnoControl") # set the default process for
                                      # Functions (see below)

Dictionary/Function
===================
Function
--------

  What we call here Function (also called Keyword in VLTSW) are objects
  containing a keyword/value pair plus extra stuff like unit, context,
  comment, ...
  Function provide some smart indexing capability:
     e.g:
     f = vlt.Function("INSi.FILTi.ENC", dtype=int) is understood to be
     a table of value because of the 'i' iterator.
     Therefore:
       f[1,2].value = 120000  # set the value of INS1.FILT1.ENC
       f[1,2] # return the corresponding Function
       f[1,2] is equivalent to f["INS1","FILT2"]
    The index 0 return the keyword without number:
       f[0,2] return the Function of "INS.FILT2.ENC"

    Also one can set value of several indexes in one command:
    f[1] = { 1:10000, 2:50000, 3:3400 } # will set value for "INS1.FILT1.ENC",
                                        # "INS1.FILT2.ENC" and "INS1.FILT3.ENC"
    so f[1,1].value is 10000, f[1,2].value is 50000, etc ...

    To know if a function contains iterable keys use the isIterable method
     Function("INSi.FILTi.ENC").isIterable() # -> true
     Function("INS1.FILT2.ENC").isIterable() # -> False
     Function("DETj.DIT").isIterable() # -> True
     Function("DET.DIT").isIterable() # -> False

    Some key methods of function object:
      - set(value) : set the value in the function and return the Function
                     itself. This allow to do quick command.
                     f.set(30000).setup() # set and then send setup (see bellow)
      - setup([value=, proc=]):
                Send a setup command with the process proc= -or if None-
                the default process defined by vlt.setDefaultProcess
                Without argument the setup is sent with the current Function
                value. Or with the value optional keyword.
                 e.g.:
                    vlt.setDefaultProcess("pnoControl")
                    f = vlt.Function("DET.DIT", 0.001)
                    f.setup(timeout=1000, expoId=0)
                    is equivalent to the system command:
         > msgSend "" pnoControl SETUP "-function DET.DIT 0.001 -expoId 0" 1000

      - status



FunctionDict
------------

  FunctionDict() objects are dictionary of Function() object.
  They are basically a collection of keyword/pair values with fast search
  keyword methods.

   Key Methods:
     - restrict : take a string or list of string and return a restricted FunctionDict
         If a string the restricted dictionary is all keys limited to the one that
         start with the input string. e.g.:
            >>> d = vlt.readDictionary("PIONIER_ICS")
            >>> d.restrict("INS.SENS1")
            return a FunctionDict like:
                  {
                  'MAX': Function("INS.SENS1.MAX", None),
                  'MEAN': Function("INS.SENS1.MEAN", None),
                  'MIN': Function("INS.SENS1.MIN", None),
                  'STAT': Function("INS.SENS1.STAT", None),
                  'VAL': Function("INS.SENS1.VAL", None)}
                  }
            One can see that the "INS.SENS1" has been droped, so one can use the
            restricted dictionary with the "MAX", "MIN", etc  keys, but also the
            full path will work :
             >>> rs = d.restrict("INS.SENS1")
             >>> rs["VAL"] #-> works
             >>> rs["INS.SENS1.VAL"] #-> works also
           So imagine you have a function that plot stuf from sensors you can parse
           the restricted dictionary. The function will not care from what ever it comes from
            >>> plotsensor( d.restrict("INS.SENS1"))
            >>> plotsensor( d.restrict("INS.SENS2"))
            etc ...
    - restricMatch : allow to return any Function that match a part of the key
        e.g :
            >>> d.restricMatch("NAME")

    - restrictContext/ restrictHasValue/ restrictClass /
      restrictHasNoValue / restrictMatch / restrictValue

     plotsensor( d.restrict("INS.SENS1"))

     - setup  : setup a bunch of Functions in one call
     - qsetup : does the same in a easier way to


Devices
-------
  Devices are derived from FunctionDict. They are a list of function wrapped
  with addiotional usefull capabilities, like e.g. : moveTo, close, etc ...
  They are defined in the devices repertory a few are set so far but that can grow.
   Motor, Shutter, Detector are three builtins

  Example to create/use a device, on Pionier:
     >>> pnoc = vlt.openProcess("pnoControl")
     >>> ics = vlt.readDictionary("PIONIER_ICS")
     >>> dispersor = vlt.devices.Motor(ics.restrict("INS.OPTI3"), statusItems=[""], proc=pnoc)
     # (proc can be also the default process vlt.setDefaultProcess(pnoc) )

     >>> dispersor.statusUpdate() # ask the instrument and update values
     >>> dispersor.moveTo("FREE") # move to FREE position
     >>> dispersor.moveTo(120000) #  move to 120000 enc position
     >>> dispersor.moveBy(10000) # offset of 10000 enc
   Also cmd_moveBy do not do anything but return the function command in a list
   so commands can be stacked together:

     >>> sh1 = vlt.devices.Shutter(ics.restrict("INS.SHUT1"))
     >>> pnoc.setup(function=dispersor.cmd_moveTo("FREE")+sh1.cmd_close())




"""
import mainvlt as vlt
from process import setDefaultProcess, getDefaultProcess
from mainvlt import EmbigousKey,  cmd, dotkey, undotkey

from .function import Function
from .functiondict import FunctionDict, functionlist
from .sequence import sequence, sequences

from . import devices

from io import openProcess, processClass, openDictionary



#import processes as proc
import glob
import os
__path__ += [os.path.dirname(__file__)+"/CDT"]
#import pnoControl

#__all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/CDT/*.py")]
