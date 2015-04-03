import numpy as np
import re
import mainvlt
import os
from .config import config
# valid default parameters types

def vltbool(val):
    return bool( val!='F' and val!=False and val)

param_types = {
    "double"  : np.float64,
    "float"   : float,
    "logical" : bool,
    "integer" : int,
    "string"  : str
    }

dictionaryPath = config["dictionarypath"]

def findDictionaryFile(dictsufix, path=None, fileprefix="ESO-VLT-DIC."):
    path = path or dictionaryPath
    if dictsufix[0:len(fileprefix)] == fileprefix:
        # the full file name is given
        fileprefix = ""

    for d in path:
        p = d+"/"+fileprefix+dictsufix
        if os.path.exists(p):
            return p
    raise ValueError("cannot find file {} in any of the path {}".format(fileprefix+dictsufix,path))


def _pname(f, value):
    f.parameterEnd()
    f.curentParameterName = value
    f.curentParameter = Parameter(name=value)
    f.dictionary[f.curentParameterName] =  f.curentParameter
    return f.readline()

def _context(f, value):
    f.curentParameter['context'] = value
    if not value in f.dictionaryContext:
        f.dictionaryContext[value] = Context()
    f.dictionaryContext[value][f.curentParameterName] = f.curentParameter
    return f.readline()

def _class(f, value):
    f.curentParameter['class'] = value
    classes = value.split("|")
    for cls in classes:
        if not cls in f.dictionaryClass:
            f.dictionaryClass[cls] = Class()
        f.dictionaryClass[cls][f.curentParameterName] = f.curentParameter
    return f.readline()

def _type(f, value):
    value = value.lower()
    if not value in f.types:
        raise TypeError("the type '%s' for parameter '%s' is unknown"%(value, f.curentParameterName))
    f.curentParameter["type"] =  f.types[value]
    return f.readline()

def _vformat(f, value):
    f.curentParameter['format'] = value
    return f.readline()

def _unit(f, value):
    f.curentParameter['unit'] = value
    return f.readline()

def _cformat(f, value):
    f.curentParameter['comment'] = value
    return f.readline()

def _description(f, value):
    desc = ""
    while True:
        spv = value.split(":",1)
        #if value[0:4] == "    ":
        if len(spv)==2 and spv[0].strip() in f.cases:
            # End of the description
            # they probably have better way to check that how ?
            f.curentParameter['description'] = desc
            return value  # return the curent lie to be treated
        if not len(value):  # end of file
            return ''
        desc += value.strip()+" "
        value = f.readline()


def _config( f, key, value):
    f.config[key] = value
    return f.readline()
def _undefined(f, key, value):
    f.curentParameter[key] = value
    return f.readline()


class Parameter(dict):
    def cmd(self, value):
        value = self['type'](value)
        return [( ".".join( re.split("[. ]",self['name']) ) , self['format']%(value))]

    def __call__(self, value):
        return self.cmd(value)

class ParameterDictionary(dict):
    _path = []
    def __getattribute__(self, key):
        if (key[0:1]=="_" and len(key)>1) or key in dict.__dict__ or key in ["cmd","cl"]:
            return super(dict, self).__getattribute__(key)
        return self.get(key)
    def cmd(self, *args, **kwargs):
        outputcmd = []
        for a in args:
            if issubclass( type(a), tuple):
                if len(a)<2:
                    raise TypeError("Expecting key/value pairs in a tuple")
                tmpcmd = self.get( a[0].upper() )
                if not issubclass( type(tmpcmd), Parameter):
                    raise TypeError("keyword '%s' results in a non Parameter object, got '%s' "%(a[0], type(tmpcmd)))
                outputcmd += tmpcmd.cmd(a[1])
            elif issubclass( type(a), list):
                outputcmd += self.cmd(*a)
            else:
                raise TypeError("expecting a tuple or a list got '%s'"%(type(a)))

        for k,v in kwargs.iteritems():
            tmpcmd = self.get(k.upper())
            if not issubclass(  type(tmpcmd) , Parameter):
                raise TypeError("keyword '%s' results in a non Parameter object, got '%s' "%(k, type(tmpcmd)))
            outputcmd += tmpcmd.cmd(v)
        return outputcmd

    def get(self, key, default=None):

        spkey = re.split("[ .]", key, 1)
        if len(spkey)>1:
            return self.get( spkey[0]).get(spkey[1])

        out = ParameterDictionary({})
        findnums = re.findall( "[0-9]+$", key)
        num = None
        if key=="_":
            key = ""

        if len(findnums):
            num = findnums[0]
            root_key = key[0:-len(num)]
            num = int(num)
            key = "%s%d"%(root_key, num)
        else:
            root_key = key

        for k in self:
            sk = re.split("[ .]", k, 1)

            if len(sk[0]) and sk[0][-1] == "i":
                rk = sk[0][0:-1]
            else:
                rk = sk[0]
            if rk==root_key:
                if len(sk)<2:
                    out[""] = self[k]
                    #p = Parameter(self[k].copy())
                    #p['name'] = " ".join(self._path+[key])
                    #return p
                else:
                    out[sk[1]] = self[k]

        if not len(out):
            raise KeyError("Cannot find keyword '%s' in the dictionary"%(key))

        if len(out)==1:
            p = Parameter(out[out.keys()[0]].copy())
            p['name'] = " ".join(self._path+[key])
            return p

        out._path = self._path + [key]
        return out
    def cl(self, clname):
        """
        Filter the keyword container by class
        """
        out = ParameterDictionary()
        for k,p in self.iteritems():
            if "class" in p:
                if clname in p['class'].split("|"):
                    out[k] = p
        return out






class Class(ParameterDictionary):
    pass
class Context(ParameterDictionary):
    pass


class Dictionary(file):
    config = {}
    dictionary = ParameterDictionary()
    dictionaryClass = {}
    dictionaryContext = {}

    types = param_types

    curentParameter = None
    curentParameterName = ""
    cases = {"Parameter Name":_pname,
             "Class":_class,
             "Context":_context,
             "Type":_type,
             "Value Format": _vformat,
             "Unit": _unit,
             "Comment Format": _cformat,
             "Comment Field": _cformat,
             "Description": _description
             }

    """
    A file descriptor for dictionary parsor

    """
    def parse(self, line=None, count = 0):
        if line is None:
            line = self.readline()


        while len(line):
            count += 1
            nline = line.strip()
            if not len(nline):
                line =  self.readline()
                continue
            if nline[0] == "#":
                line = self.readline()
                continue


            spline = nline.split(":", 1)
            if len( spline)<2:
                line = self.readline()
                continue

            key, value = spline
            key = key.strip()
            value = value.strip()

            if not key:
                line = self.readline()
                continue

            if self.curentParameter is None and not key=="Parameter Name":
                line =  _config(self, key, value)
                continue

            if not key in self.cases:
                line = _undefined(self,key, value )

            line = self.cases[key](self, value)

        return count

    def parameterEnd(self):
        self.curentParameter = None
        self.curentParameterName = ""


def parameter2function(param):
    return mainvlt.Function( param['name'], param['type'], format=param.get("format", "%s"),
                         default=None, value=None, index=None,
                         comment=param.get("comment", "%s"), description=param.get("description", ""), unit=param.get("unit", ""), context=param.get("context", ""), cls=param.get("class", "").split("|"))

def parameterDictionary2functionDict( pdictionary):
    out = mainvlt.FunctionDict()
    for k,p in pdictionary.iteritems():
        out[k] = parameter2function(p)
    return out


