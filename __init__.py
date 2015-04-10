import mainvlt as vlt
from process import setDefaultProcess, getDefaultProcess
from mainvlt import EmbigousKey,  cmd, dotkey, undotkey

from .function import Function
from .functiondict import FunctionDict, functionlist
from .sequence import sequence, sequences

from . import devices

from io import openProcess, processClass, readDictionary



#import processes as proc
import glob
import os
__path__ += [os.path.dirname(__file__)+"/CDT"]
#import pnoControl

#__all__ = [ os.path.basename(f)[:-3] for f in glob.glob(os.path.dirname(__file__)+"/CDT/*.py")]
