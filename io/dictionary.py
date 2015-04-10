from .keywords import KeywordFile
from ..function import Function
from ..functiondict import FunctionDict
from ..config import config
from ..mainvlt import formatBoolFunction
import os
import numpy as np

def _new_parameter(f, key, value, more):
    if f.in_header:
        f.end_header()
    f.open_parameter(value)

def _start_header(f, key, value, more):
    f.start_header()
    f.set([key], value)

def _add(p,n):
    return p+"\n"+n

class Dictionary(KeywordFile):
    curentParameter = None
    curentField = None
    inField  = False
    inHeader = True

    cases = {
        "Dictionary Name": _start_header,
        "Parameter Name" : _new_parameter
    }

    def open_parameter(self, name):
        self.curentParameter = name
    def close_parameter(self):
        self.curentParameter = None
    def open_field(self, name):
        self.curentField = name
    def close_field(self):
        self.curentField = None

    def key2path(self, key):
        if not self.curentParameter:
            return [key]
        if self.inField:
            return self.curentParameter, key, _add

        return self.curentParameter, key
    def match_line(self, line):
        if line[0:2] == "  ":
            if self.curentField:
                self.inField = True
                return self.curentField, line.strip(), ""
            return None, None, ""

        self.inField = False

        # m = self.reg.match(line.strip())
        # if not m:
        #     return None, None, ""
        # groups = m.groups()
        groups = line.split(":",1)
        if len(groups)<2:
            return None, None, ""
        key, value = groups[0].strip(), groups[1].strip()
        self.open_field(key)

        return key, value, ""

param_types = {
    "double"  : np.float64,
    "float"   : float,
    "logical" : bool,
    "integer" : int,
    "string"  : str
    }

def _dictionary_type(value):
    value = value.lower()
    if not value in param_types:
        raise TypeError("the type '%s' for parameter '%s' is unknown"%(value, f.curentParameterName))
    return param_types[value]
def _dictionary_format(dtype,format):
    if dtype is bool:
        return formatBoolFunction
    return format


def parameter2function(key, param, cls=Function):
    dtype = _dictionary_type(param.get("Type","string"))
    format= _dictionary_format(dtype, param.get('Value Format', "%s"))
    return cls(key,
               dtype = dtype,
               cls = param.get('Class', "").split("|"),
               context = param.get('Context', ""),
               description = param.get('Description', ""),
               unit = param.get('Unit',None),
               format = format,
               comment = param.get('Comment Format',
                                   param.get('Comment Field',"")
                                   )
               )

def parameters2functiondict(params, cls=FunctionDict):
    return cls({key:parameter2function(key, param) for key,param in params.iteritems()})

def findDictionaryFile(dictsufix, path=None, fileprefix=None):
    """ look for the coresponding dictionary file in the path list
    default path list is dictionarypath in vlt.config

    keywords
    --------
    fileprefix = "ESO-VLT-DIC."
    """
    fileprefix = fileprefix or config["dictionaryprefix"]
    path = path or config["dictionarypath"]

    if dictsufix[0:len(fileprefix)] == fileprefix:
        # the full file name is given
        fileprefix = ""

    for d in path:
        p = d+"/"+fileprefix+dictsufix
        if os.path.exists(p):
            return p
    raise ValueError("cannot find file {} in any of the path {}".format(fileprefix+dictsufix,path))


def readDictionary(dictionary_name, path=None):
    file_name = findDictionaryFile(dictionary_name, path=path)
    f = Dictionary(file_name)
    f.parse()
    return parameters2functiondict(f.parameters)




