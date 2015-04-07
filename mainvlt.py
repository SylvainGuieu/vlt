#!/usr/bin/python
import os
import commands
import re

from .config import config


msgSend_cmd = "msgSend"
debug = not os.getenv("HOST")  in ["wbeti" , "wpnr" , "wbeaos"]

verbose = 1
_defaultProcess = None

LASTBUFFER = ""
DEFAULT_TIMEOUT = None

KEY_MATCH_CASE = False


#################
# Used in cdt process definition

def msg_send_decorator(msg, commands):
    def tmp(self, timeout=None, **kwargs):
        return self.msgSend(msg, kwargs, timeout=timeout)
    tmp.__doc__ = form_cmd_help(msg,commands[msg])
    return tmp


def form_cmd_help(msg,command):
    return msg+"("+" ,".join(k+"=%s"%o.dtype for k,o in command.options.iteritems())+")\n\n"+command.helpText


############################################################
# Some functions which are used as dtype or format
############################################################

def setDefaultProcess(proc):
    """ set the default process for the vlt module """
    global _defaultProcess
    if not isinstance(proc, Process):
        raise ValueError("Expecting a Process got %s"%type(proc))
    _defaultProcess = proc


def getDefaultProcess():
    """ return the default process of the vlt module """
    global _defaultProcess
    if _defaultProcess is None:
        raise Exception("There is no default process define, use setDefaultProcess to set")
    return _defaultProcess

def getProc(proc=None):
    return proc if proc is not None else getDefaultProcess()


def dtypeFunctionList(function):
    """
    write a command line based on an array of tuple :
      [("cmd1","opt1"),("cmd2","opt2"), ...]
    or an array of string ["cmd1 opt1", "cmd2 opt2", ...]
    e.g:
       dtypeFunctionList ( [("cmd1","opt1"),("cmd2","opt2"), ...])
       will return "cmd1 opt1 cmd2 opt2 ..."
    This function is used for instance in message send command

    if the unique argument is a str, it is returned as it is.
    argument can also be a FunctionDict or a System object, in this case
    the command for all functions with a values set is returned.
    """
    if issubclass(type(function), str):
        return function
    if issubclass(type(function), (FunctionDict, System)):
        return "{}".format(function)
    if issubclass(type(function), Function):
        return dtypeFunctionList(function.cmd())

    function = cmd(function) #to make sure it is a flat list
    out = []
    for func in function:
        if issubclass( type(func), tuple):
            if len(func)!=2:
                raise TypeError("Expecting only tuble of dim 2 in setup list")
            if isinstance( func[1], str):
                fs = func[1].strip()
                if fs.find(" ")>-1:
                    out.append("%s '%s'"%(func[0],fs))
                else:
                    out.append("%s %s"%(func[0],fs))
            else:
                out.append("%s %s"%func)
        else:
            out.append("%s"%(func))
    return " ".join(out)


def dtypeFunctionListMsg(function):
    if issubclass( type(function), str) :
        return function
    if issubclass( type(function), (FunctionDict)):
        return " ".join( [f.getMsg() for f in function] )
    if issubclass( type(function), (Function)):
        return function.getMsg()
    return " ".join(function)


def formatBoolFunction(value):
    """
    return "T" or "F" if the input boolean value is True or False.
    Used to format VLT message command
    """
    if value:
        return "T"
    return "F"


def formatBoolCommand(value):
    """ this return an empty string.
    Used to format boolean values in commands, they do not accept
    argument
    """
    # command does not accept argument when they are boolean
    return ""


class Option(object):
    """
    Option class for VLT command.
    Option have is a pair of key (or message) and value

    for instantce in:
        msgSend "" pnoControl SETUP "-function DET.DIT 0.005 DET.NDIT 1000 -expoId 0"

    'function' and 'expoId' are Option

    p = Option(msg, dtype)
    """
    default = None
    format  = "%s"
    def __init__(self, msg, dtype , format="%s", default=None, name=""):
        self.name  = name #not used
        self.msg   = msg
        self.dtype = dtype
        if default is not None:
            self.default = self.parseValue(default)
        self.format= format

    def __str__(self):
        if self.default is None:
            dfs = "None"
        else:
            default = self.getDefault()
            if issubclass(type(default), str):
                dfs = "'%s'"%(self.getFormatedDefault())
            else:
                dfs = self.getFormatedDefault()
        return """%s("%s", %s, default=%s, format="%s")""" % (self.__class__.__name__, self.msg, self.dtype, dfs, self.format)

    def __repr__(self):
        return self.__str__()

    def cmd(self, value=None):
        if value is None:
            value = self.default
        msg = self.msg
        return cmd((msg, self.formatValue(value)))

    def getDefault(self):
        """ Return the default value for this Option """
        return self.parseValue(self.default)

    def setDefault(self, value):
        """ Set the default value for this Option """
        self.default = self.parseValue(value)

    def getFormatedDefault(self):
        """ return the fromated defaultValue if any """
        if self.default is None:
            return ""
        return self.formatValue(self.default)

    def parseValue(self, value):
        """ Parse the value according to the dtype of this Option
        The parsed value is returned.
        e.g:
        o = Option("expoId",int)
        o.parse("45") # return int(45)
        """
        try:
            return self.dtype(value)
        except ValueError:
            raise ValueError("Cannot convert '%s' to the expecting type %s for param '%s'"%(value,self.dtype, self.msg))

    def formatValue(self, value):
        """ Parse and format value according to the dtype and format """
        value = self.parseValue(value)
        # format can be a string or a function
        if issubclass(type(self.format), str):
            return self.format%(value)
        else:
            return self.format(value)


class Actions(object):
    def __init__(self, *args, **kw):
        parent = kw.pop("parent",None)
        if len(kw):
            raise KeyError("Actions take only parent has keyword")

        self.actions = {}
        self.actionCounter = 0
        self.stopped = False
        self.parent = parent
        for action in args:
            self.addAction(action)

    def stop(self):
        self.stopped = True
    def release(self):
        self.stopped = False


    def addAction(self, action):
        if not hasattr(action, "__call__"):
            raise ValueError("action must have a __call__attribute")
        self.actionCounter += 1
        self.actions[self.actionCounter] = action
        return self.actionCounter

    def remove(self, id):
        if not id in self.actions:
            raise KeyError("Cannot find an action connected with id %s"%id)

        del self.actions[id]
    def pop(self, id, default=None):
        return self.actions.pop(id, default)

    def clear(self):
        return self.actions.clear()

    def run(self, *args, **kwargs):
        if self.stopped: return
        if not self.actionCounter: return
        if self.parent:
            self.parent.run(*args, **kwargs)

        keys = self.actions.keys()
        keys.sort()
        for k in keys:
            self.actions[k](*args, **kwargs)

    def copy(self):
        return self.__class__( **self.actions )

    def derive(self):
        return self.__class__(parent=self)

    def __len__(self):
        if self.parent:
            return len(self.parent) + len(self.actions)
        return len(self.actions)

    def __call__(self, action):
        return self.addAction(action)


class FunctionMatch(object):
    def __init__(self, indexes, partialy, prefix="", suffix=""):
        """ A simple class returned by Function match
        m = f.match("SOME.KEY")
        m.indexes is None if f is not iterable (see Function)
        m.indexes is  a tuple of indexes if f is iterable
        m.partialy is True if the key is partialy matched
        if partialy matched m.prefix and m.suffix return what is before
        and after the match
        """
        self.indexes  = indexes
        self.partialy = bool(partialy)
        self.prefix = str(prefix)
        self.suffix = str(suffix)


class FunctionMsg(object):
    def __init__( self, valin, sep=None):
        if isinstance(valin, str):
            if sep is None:
                vspace, vdot = valin.split(" "), valin.split(".")
                valin, sep = (vspace, " ") if len(vspace)>len(vdot) else (vdot, ".")
            else:
                valin = valin.split(sep)
        self.keys = []
        for s in valin:
            k = matchKey(s)
            if k is None:
                raise KeyError("the Key '%s' is not valid in '%s'" % (s,valin))
            self.keys.append(k)
        #self.keys = [matchKey(s) or s for s in valin]
        self.sep = sep or "."

    @classmethod
    def new(cls, keys, sep="."):
        """ Return a new FunctionMsg object with the same message """
        new = cls([], sep=sep)
        new.keys = keys
        return new

    def match(self, keys, prefixOnly=False, partialy=True):
        """ match if the input keys match this message.
        Return a FunctionMatch object if the match is succesful else None

        By default partialy=True, means that the message can be matched
        if only a part of it is matched.
        e.i:
        import vlt
        vlt.FunctionMsg("INS.OPT1.NAME").match("OPT1") # match
        vlt.FunctionMsg("INS.OPT1.NAME").match("NAME") # match
        vlt.FunctionMsg("INS.OPT1.NAME").match("NAME", prefixOnly=True) # NO match
        vlt.FunctionMsg("INS.OPT1.NAME").match("INS.OPT1", prefixOnly=True) match
        vlt.FunctionMsg("INS.OPT1.NAME").match("NAME", partialy=True) # NO match
        etc ....

        """
        if not isinstance(keys, FunctionMsg):
            keys = FunctionMsg(dotkey(keys))

        keyslen = len(keys.keys)


        selfkeyslen = len(self.keys)
        if keyslen>selfkeyslen: return None
        partialy = (partialy and (selfkeyslen != keyslen))

        if partialy or prefixOnly:
            it = [0] if prefixOnly else range(selfkeyslen-keyslen+1)
            for i in it:
                prefix = FunctionMsg.new(self.keys[0:i]           , self.sep)
                suffix = FunctionMsg.new(self.keys[i+keyslen:None], self.sep)
                trimed = FunctionMsg.new(self.keys[i:i+keyslen]   , self.sep)
                m = trimed.match(keys)
                if m:
                    newindexes = tuple(list(prefix.getIndex())+list(m.indexes or []))
                    return FunctionMatch(newindexes, True, prefix.reform(), suffix.reform())
                    return m
            return None
        else:
            if keyslen != selfkeyslen: return None
            indexes = []

            for k, sk in zip(keys.keys,self.keys):
                m = sk.match( k )
                if m is False: return None
                if m is True: continue
                indexes.append( m )
        return FunctionMatch(tuple(indexes), partialy)
        #if len(indexes):
        #return FunctionMatch(None, partialy)

    def reIndex(self, indexes):
        """
        Return a new re-indexed FunctionMsg if it is indexable.
        The entry is a tuple of index the len of the tuple should not
        exceed the number of indexable keys.

        parts of FunctionMsg, Keys, are indexable if they have i,j,h or k at the
        end.
        The 0 index means that index number is removed.

        e.g :  "INSi" is considered as iterable
               "INSi.OPTi" is twice iterable
        > vlt.FunctionMsg("INSi.OPTi.NAME").reIndex( (1,2) )
        will return  vlt.FunctionMsg('INS1.OPT2.NAME')
        > vlt.FunctionMsg("INSi.OPTi.NAME").reIndex( (1,) )
        will return  vlt.FunctionMsg('INS1.OPTi.NAME')
        > vlt.FunctionMsg("INSi.OPTi.NAME").reIndex( (1,2,1) )
        will Raise a IndexError

        > vlt.FunctionMsg("INSi.OPTi.NAME").reIndex( (0,2) )
        will return  vlt.FunctionMsg('INS.OPT2.NAME')

        """
        if not isinstance( indexes, tuple):
            raise ValueError( "expecting a tuple has unique argument got %s"%type(indexes))
        offset = 0
        out = []
        indexeslen = len(indexes)
        for ik in self.keys:
            if ik.iterable and offset<indexeslen:
                out.append( ik.reIndex(indexes[offset]))
                offset +=1
            else:
                out.append(ik)
        if offset<indexeslen:
            raise IndexError("to many indices (%d) for key %s"%(indexeslen, self))

        return self.new( out , self.sep)
    def getIndex(self):
        #if not self.isIterable():
        #    return tuple()

        return tuple( [s.index for s in self.keys if s.isIterable()] )

    def reform(self, sep=None):
        sep = sep or self.sep
        return sep.join( s.reform() for s in self.keys)
    def reformAll(self, sep=None):
        sep = sep or self.sep
        out = [""]
        first = True
        for s in self.keys:
            keys= s.reformAll()
            tmp = []
            for i,o in enumerate( out):
                for k in keys:
                    tmp.append(o+("" if first else sep)+k)
            out =  tmp
            first = False
        return out

    def isIterable(self):
        #print "AAAAAA", self.keys
        return any(s.isIterable() for s in self.keys)
    def __repr__(self):
        return "'%s'"%self.reform()
    def __str__(self):
        return self.reform()
    def __getitem__(self, item):
        if not isinstance(item , tuple): item = (item,)
        return self.reIndex(item)


class FunctionKeyi(object):
    iterable = True
    re = re.compile(r'([^ijkl]*)([ijkl])$')
    mkey   = 0
    mindex = 1
    def __init__(self, strin,  index=""):
        self.key = str(strin)

        if isinstance( index, str):
            self.strindex = index
            self.readIndex(index)
        else:
            self.index = index
            self.strindex = self.writeIndex

    @classmethod
    def matchNew(cls, strin):
        m = cls.re.match(strin)
        if m:
            g = m.groups()
            new = cls(g[cls.mkey], g[cls.mindex])
            return new
        return None

    def match(self, key, prefixOnly=False):
        if not isinstance(key, FunctionKeyi):
            key = matchKey(key)
        if key.key != self.key:
            if KEY_MATCH_CASE: return False
            if key.key.upper() != self.key:
                return False

        if key.index == None:
            " For an iterable KEY is equivalent to KEY0 "
            if self.index == None and isinstance(key, FunctionKey):
                return 0
            return None
        try:
            return self.reIndex(key.index or 0).index
        except IndexError:
            return False

    def readIndex(self, strindex):
        if not strindex in "ijkl":
            raise Exception("index should only be i,j,k or l")
        self.index = None

    @staticmethod
    def _writeIndex(index):
        if index is None:
            return "i"
        if index == 0:
            return ""
        return "%d"%(index)
    @classmethod
    def _reform(cls, key, index):
        return "%s%s"%(key, cls._writeIndex(index))

    def getIndex(self):
        if not self.isIterable():
            raise IndexError("'%s' is not iterable "%self)
        return self.index

    def isIterable(self):
        return self.iterable

    def hasIndex(self):
        return True

    def hasLen(self):
        return False

    def writeIndex(self):
        return self._writeIndex( self.index)

    def reIndex(self, newindex):
        if self.index is not None:
            raise IndexError("Key %s not iterable"%self)

        if newindex is None:
            return FunctionKeyi( self.key, None) # return a copy

        if isinstance(newindex, str):
            m = matchKey(newindex)
            if m.key != self.key:
                raise IndexError("'%s' does not match %s"%(newindex,self))
            newindex = m.index or 0

        if isinstance(newindex, slice):
            start, stop = newindex.start or 0 , newindex.stop
            if stop is None:
                raise IndexError("stop slice mandatory")
            return FunctionKeySlice( self.key, slice(start, stop))

        if hasattr(newindex, "__iter__"):
            return FunctionKeyList( self.key, list( newindex))

        # the return key is no longer iterable, return a string
        return FunctionKey(self.key, newindex)


    def reform(self):
        return self._reform( self.key, self.index)

    def reformAll( self):
        return [self.reform()]

    def __repr__(self):
        return "'%s'"%self.reform()
    def __str__(self):
        return self.reform()
    def __getitem__(self, item):
        return self.reIndex(item)


class FunctionKey(FunctionKeyi):
    iterable = False
    #re = re.compile(r'^([^0-9][0-9a-zA-Z_-]*)([0-9]*)$')
    re = re.compile(r'^(.+[^0-9]|.)([0-9]*)$')
    #rei = re.compile(r'^([0-9]+)$')
    #@classmethod
    #def matchNew(cls, strin):
    #    m = cls.re.match(strin)
    #    if m :
    #        mindex = m.groups()[0]
    #        return cls( strin[0:-len(mindex)], mindex)
    #    else:
    #        return cls( strin, "")

    def readIndex(self, strindex):
        if strindex=="":
            self.index = None
        else:
            self.index = int(strindex)

    @staticmethod
    def _writeIndex(index):
        if index==0 or index is None:
            return ""
        return "%d"%index

    def reIndex(self, dummy):
        raise IndexError("Not iterable key %s"%self)
    def match( self, key):
        selfkey = self.reform()
        key = "%s"%key #keep "%" to reform in case of FunctionKey instance
        if KEY_MATCH_CASE:
            return selfkey==key
        else:
            return selfkey==key or selfkey==key.upper()
    def hasIndex(self):
        return not (self.index is None)


class FunctionKeyList(FunctionKeyi):
    re = re.compile(r'([^[]*)[(]([0-9, ]*)[)]$')  # ])

    maxlenIndexWrite = 8

    def readIndex(self, strindex):
        self.index = map(int, strindex.split(","))

    @classmethod
    def _writeIndex(cls, index):
        ilen = len(index)
        if ilen >cls.maxlenIndexWrite:
            return "(%s,...,%s)"%(
                ",".join( map(str,index[0:cls.maxlenIndexWrite/2-1])),
                ",".join( map(str,index[-cls.maxlenIndexWrite/2+1:None]))
                )
        return "(%s)"%(",".join(map(str,index)))
    def hasLen(self):
        return True
    def __len__(self):
        return len(self.index)

    def __iter__(self):
        self.iternum = -1
        return self
    def next(self):
        self.iternum += 1
        if self.iternum<len(self):
            return FunctionKeyi( self.key, self.index[self.iternum])
        raise StopIteration()

    def reIndex(self, newindex):
        # if None juste return the same index
        if newindex is None:
            return FunctionKeyList(self.key, list(self.index))

        if isinstance(newindex, str):
            m = matchKey(newindex)
            if m.key != self.key:
                raise IndexError("'%s' does not match %s"%(newindex,self))
            newindex = m.index or 0


        if isinstance(newindex, slice):
            start, stop = newindex.start or 0 , max(self.index) if newindex.stop is None else newindex.stop

            if (start<min(self.index)) or (stop>max(self.index)):
                raise IndexError("Slice out of range for index %s"%self.writeIndex())
            return FunctionKeyList( self.key , [ i for i in self.index if i>=start and i<=stop ])

        if hasattr(newindex, "__iter__"):
            for i in newindex:
                if not i in self.index:
                    raise IndexError("index '%d' is not included"%i)
            return FunctionKeyList(self.key , list(newindex))

        if not newindex in self.index:
            raise IndexError("index '%d' is not included"%newindex)
        return FunctionKey(self.key, newindex )
        #return FunctionKeyi(self.key , newindex )
    def reformAll(self):
        return [FunctionKeyi(self.key, j).reform() for j in self.index]


class FunctionKeySlice(FunctionKeyi):
    #re = re.compile(r'([^[]*)[(]([0-9]*:[0-9]*:[0-9]*|[0-9]*:[0-9]*)[)]$')
    re = re.compile(r'([^[]*)[(]([0-9]+->[0-9]+)[)]$')  # ])
    def readIndex(self, strindex):
        vals = map(int, strindex.split("->"))
        self.index = slice(*vals)

    @staticmethod
    def _writeIndex(index):
        return "(%s->%s)"%(index.start, index.stop)

    def __len__(self):
        return self.index.stop-self.index.start+1

    def __iter__(self):
        self.iternum = self.index.start-1
        return self

    def next(self):
        self.iternum += 1
        if self.iternum<=self.index.stop:
            return FunctionKeyi( self.key, self.iternum)
        raise StopIteration()


    def reIndex(self, newindex):
        if newindex is None:
            return FunctionKeySlice(self.key , self.index)

        if isinstance(newindex, str):
            m = matchKey(newindex)
            if m.key != self.key:
                raise IndexError("'%s' does not match %s"(newindex,self))
            newindex = m.index or 0

        if isinstance(newindex, slice):
            start, stop = newindex.start or 0 , max(self.index) if newindex.stop is None else newindex.stop
            if start<self.index.start or stop>self.index.stop:
                raise IndexError("Slice out of range for range %s"%self.writeIndex())
            return FunctionKeySlice(self.key ,slice( start, stop))

        if hasattr(newindex, "__iter__"):
            for i in newindex:
                if i<self.index.start or i>self.index.stop:
                    raise IndexError("index '%d' is not included"%i)
            return FunctionKeyList(self.key ,  list(newindex))

        if newindex<self.index.start or newindex>self.index.stop:
            raise IndexError("index '%d' is not included"%newindex)
        return FunctionKey(self.key, newindex)

    def reformAll(self):
        return [ FunctionKeyi(self.key, j).reform() for j in range(self.index.start, self.index.stop+1) ]


        #return FunctionKeyi(self.key , newindex)

def matchKey(key):
    return FunctionKeyi.matchNew(key) or FunctionKeyList.matchNew(key)  or FunctionKeySlice.matchNew(key) or FunctionKey.matchNew(key)

def upperKey(key):
    ukey = key.upper()
    if key[-1] in ["i", "j", "k"]:
        if key[0:-1] == ukey[0:-1]:
            return key
    return ukey



class Function(object):
    """
    Function is basicaly an object carrying a keyword (called also function
    in vlt software) and a value.
    It represent any keywords found in vlt dictionaries with special and very useful
    behavior for iterable keys like e.g "DETi WINi"
    On top of a keyword/value pair it carries numerous parameters (see bellow).

    Parameters
    ----------
    msg   : The keyword, the message function e.g. "DET DIT" same as "DET.DIT"
    value (=None) : Value corresponding to function can be None if no value is set

    default (=None): a default value if value is not set (e.i =None)

    format (="%s"): the str python format to represent the object when passed
                    in command e.g.: "%2.3f" format can also be a function
                    accepting one argument (the value) and returning a string

    dtype (=None): the data type, e.g: float, int, str, ... can also be a function
    unit (="")   : value unit

    comment (="") : value comment
    description (="") : value desciption
    context (="") : data vlt context, e.g. "Instrument"
    cls (=[])     : list of vlt class e.g.: ['header', 'setup']
    statusFunc (=None) : a string or Function used to send a status command,
                         default is the Function msg itself.


    Attributes
    ----------
    copy(copyValue) : make a copy

    info()    : print useful information about the Function
    infoStr() : return a string with useful information about the Function
    infoDict(): return a dictionary containing the same info printed in infoStr



    """
    default   = None
    value     = None
    index     = None
    #_num_re = re.compile(r'([^#]*)[#]([^#]*)')
    #_num_re = re.compile(r'([^i]*)[i]([. ]*|$)')
    _num_re = re.compile(r'([^i]*)[i]([^i]*)')
    _num_reList  = re.compile(r'([^[]*)[[]([0-9,]*)[]]([^]]*)')  # ]
    _num_reSlice = re.compile(r'(.*)([0-9]*:[0-9]*:[0-9]*|[0-9]*:[0-9]*)(.*)')

    _num_re1      = re.compile(r'([^i]*)([i])$')
    _num_reList1  = re.compile(r"([^[]*)[[]([0-9,]*)[]]$") # ])
    _num_reSlice1 = re.compile(r'([^[]*)[[]([0-9]*:[0-9]*:[0-9]*|[0-9]*:[0-9]*)[]]$') # ])

    _num_re2      = re.compile(r'^[i]$')
    _num_reList2  = re.compile(r'^([0-9,]*)$')
    _num_reSlice2 = re.compile(r'^([0-9:]*)$')

    format = "%s"
    def __init__(self, msg, value=None, dtype=None, format="%s", default=None,
                 index=None, comment="", description="", unit="", context="",
                 cls=None, selected=False,   statusFunc=None,
                 _void_=False):
        if _void_: #_void_ is for internal use only. To create an empty instance
                   #_void_ is used by _new and therefor the copy funtions
            return
        self.params = {}

        self.onValueChange = Actions()
        self.onSetup       = Actions()
        self.onSelect      = Actions()
        self.onUnSelect    = Actions()

        self.selected   = False
        self.statusFunc = statusFunc

        self.setMsg(msg) # set the message. This will decide if it is aniterable Function




        self.index= index

        if dtype is None:
            dtype = str if value is None else type(value)
        self.setFormat(format)
        self.setDtype(dtype)

        self.setValue(value)

        self.setDefault(default)
        self.setComment(comment)
        self.setDesciption(description)
        self.setUnit( unit)
        self.setContext( context)
        self.setCls( cls)



    def _new(self, **attr):
        return self._copyAttr(self.__class__("",_void_=True), **attr)

    def _copyAttr(self,new, **attr):
        for k in ["params", "msg","value", "index", "onValueChange", "onSetup","onSelect", "onUnSelect", "selected", "statusFunc"]:
            setattr( new, k,  attr[k] if k in attr else getattr(self, k) )
        return new

    @classmethod
    def newFromCmd(cls, cmd, fromdict=None):
        """
        Build a new Function object from a tuple.

        This function provide a quick way to build a function. Usefull to
        parse a string into a python vlt Function object.
        It try to be smart at gessing the righ dtype: e.g  '5' will be a int
         '5.6' will be a float, 'T' will be True, etc ...
        if the value cannot be converted to numerical or boolean it is
        considered as a string.
        The tuple can have:
          1 element: key, value stay None and dtype is str
          2 elements:  key and value, dtype is guessed
                    or key and dtype, value stay None
          3 elements:  key, value, dtype
          4 elements:  key, value, dtype, format
        A string "KEY val" will be converted to ("KEY", "Val")


        example:
        newFromCmd(("INS.OPT1.ENC", 250000))
        newFromCmd("INS.OPT1.ENC  250000")
        newFromCmd(("INS.OPT1.ENC", 250000, str)) # to Force beeing a string


        """
        if issubclass(type(cmd), basestring):
            cmd = tuple(s.strip() for s in cmd.split(" ",1))

        if issubclass(type(cmd), tuple):
            if len(cmd)==4:
                msg, sval, dtype, format = cmd
            elif len(cmd)==3:
                msg, sval, dtype = cmd
                format = None
            elif len(cmd)==2:
                msg, sval = cmd
                dtype, format = None, None
            elif len(cmd)==1:
                msg, = cmd
                sval, dtype, format = None, str, None
            else:
                raise ValueError("command expected to be a tuple with 2,3 or 4 elements")

            if not issubclass(type(msg), basestring):
                raise ValueError("The first element of the tuple must be string")

        else:
            raise ValueError("cmd should be s tuple or a string got %s" % (cmd,))

        # Try to guess the dtype from the value
        if dtype is None:
            if dtype is None and isinstance(sval, basestring):
                try:
                    val = int(sval)
                except:
                    try:
                        val = float(sval)
                    except:
                        if sval is "T":
                            val = True
                        elif sval is "F":
                            val = False
                        else:
                            val = sval
            else:
                val = sval
            if isinstance(val, type):
                val, dtype = None, val
            else:
                dtype = type(val)
        else:
            val = sval

        if fromdict is not None and msg in fromdict:
            return fromdict[msg].new(val)

        return cls(msg, value=val, dtype=dtype)

    #_mod_re = re.compile(r"[%]([+-*]*[0-9]+)([^%])")
    def __rmod__(self, f_rep):

        return 0
    def __repr__(self):
        if not self.hasDefault():
            dfs = "None"
        else:
            default = self.getDefault()
            if issubclass(type(default), str):
                dfs = "'%s'"%(self.getFormatedDefault())
            else:
                dfs = self.getFormatedDefault()

        if not self.hasValue():
            vfs = "None"
        else:
            value = self.getValue()
            if issubclass(type(value), str):
                vfs = "'%s'"%(self.getFormatedValue())
            else:
                vfs = self.getFormatedValue()

        return """{classname}("{msg}", {value})""".format(classname=self.__class__.__name__, msg=self.getMsg(), value=vfs)

        ##return """%s("%s", %s,  format="%s", default=%s, value=%s)"""%(self.__class__.__name__, self.getMsg(), self.getDtype(), self.format, dfs, vfs)

    def __str__(self):
        return self.__repr__()
        if not self.hasValue():
            raise Exception("The element '%s' does not have value and cannot be formated"%(self.getMsg()))
        return self.getFormatedValue()

    def info(self):
        """
        Print usefull information about the function
        """
        print self.infoStr()

    def infoStr(self):
        """
        Returns
        -------
        A string representing useful information about the function
        """
        return """{iterable}Function of message {msg}
  value  = {value}
  default = {default}

  format = {format}
  type   = {type}
  unit   = {unit}

  class : {cls}
  context : {context}
  comment : {comment}
  description: {description}

  onValueChange: {nonvaluechange:d} actions
  onSetup: {nonsetup:d} actions
""".format(**self.infoDict())
    def infoDict(self):
        """
        Returns
        -------
        A dictionary containing useful/printable information about the function
        """
        if not self.hasDefault():
            default = "None"
        else:
            default = self.getDefault()
            if issubclass(type(default), str):
                default = "'%s'"%(self.getFormatedDefault())
            else:
                default = self.getFormatedDefault()


        if not self.hasValue():
            value = "None"
        else:
            value = self.getValue()
            if issubclass(type(value), str):
                value = "'%s'"%(self.getFormatedValue())
            else:
                value = self.getFormatedValue()


        return dict(
            msg = self.getMsg(),
            iterable = "iterable " if self.isIterable() else "",
            value= value,
            default=default,
            format=self.getFormat(),
            type = self.getDtype(),
            unit = self.getUnit(),
            cls  = self.getCls(),
            context = self.getContext(),
            comment = self.getComment(),
            description = self.getDescription(),
            nonvaluechange = len(self.onValueChange),
            nonsetup = len( self.onSetup)
        )

    def __format__(self, format_spec, context=None):
        if not len(format_spec):
            return format( self.getFormatedValue(context=context), format_spec)
        #    format_spec = "s"
        #if format_spec[-1]=="s":
        #    return format( self.getFormatedValue() , format_spec)

        if format_spec[-1]=="m":
            return format( self.getMsg(), format_spec[0:-1]+"s")

        if format_spec[-1]=="c":
            return format( cmd2str(self.cmd(context=context)), format_spec[0:-1]+"s")

        return format(self.getValue(context=context), format_spec)

    def copy(self,copyValue=False):
        """
        make a copy of the function
        Parameters
        ----------
        copyValue (=False) : if True make a copy of the value, this has effect only if
            the function is iterable
        Return
        ------
        a new Function object sharing same parameters (unit,format, etc...)
        """
        new = self._new()
        if copyValue:
            if self.hasValue():
                new.setValue(self.getValue()) #This will copy the values if it is an iterable
        return new


    def new(self, value):
        """
        new (value)
        Return a copy of the Function parameter with the new value set.
        """
        if self.isIterable():
            raise TypeError("new works only on none iterable keys")
        return  self._new(value=self.parseValue(value))


    def __getitem__(self, item):

        if isinstance(item, str):
            m = self.msg.match(item)
            if not m :
                raise KeyError("Function '%s' dos not match '%s'"%(self.msg, item))
            item = m.indexes

        if not isinstance( item , tuple):
            item = (item,)
        if len(item) and not self.isIterable():
            raise IndexError("Function '%s' is not iterable, accept only an empty tuple"%self.getMsg())


        #item = itemExplode(item)

        return self._getOrCreate(item)

    def __tmpgetitem__(self, item):

        if not isinstance( item , tuple):
            item = (item,)

        stritems = sum(1 for i in item if isinstance(i, str) )

        if stritems>1:
            raise IndexError("Accept only a int indexes or a single string")

        if stritems != len(item):
            if not self.isIterable():
                if len(item)==1 and item[0] is None:
                    return self
                raise IndexError("got a int index but the value of this parameter '%s' is not iterable"%(self.getMsg()))
            item = itemExplode(item)
            if isinstance( item , list):
                 return self.todict(item)
            return self._getOrCreate(item)

        ## case it is a str
        item = item[0]
        if not len(item):
            return self.getValue()
        attr = "get%s"%(item[0].capitalize()+item[1:None])
        return self.__getattribute__( attr)()

    def __setitem__(self, item, value):
        self[item].set(value)

    def __iter__(self):
        if not self.isIterable():
            raise Exception("function '%s' is not iterable"%(self.getMsg()))
        return self.value.__iter__()

        return FunctionIter(self)

    def _rebuildIndex(self, new):
        new = self.getFunctionMsg().reIndex(tuple(new))
        if new.isIterable(): return new.getIndex()
        return None

    def _save_rebuildIndex(self, new):
        orig = self.index
        if not orig: return new, [True]*len(new)
        if not new : return list(orig), [False]*len(orig)
        out = []
        isi = []
        offset = 0


        for i in orig:
            if isinstance(i,slice): i = range(i.start or 0, i.stop or 1, i.step or 1)
            if i is None:
                out.append(new[offset])
                isi.append(True)
                offset +=1
            elif hasattr(i,"__iter__"):
                inew = new[offset]
                if hasattr(inew,"__iter__"):
                    for j in inew:
                        if not j in i:
                            raise IndexError("Index %d  excluded"%j)
                if isinstance(inew, slice):
                    if (min(i)>inew.start) or (max(i)<inew.stop):
                        raise IndexError("Range %d:%d  excluded"%(inew.start,inew.stop))

                elif (inew is not None) and (not inew  in i):
                    raise IndexError("Index %d  excluded"%inew)
                out.append(inew)
                isi.append(True)
                offset +=1

            else:
                out.append(i)
                isi.append(False)
        return tuple(out), isi


    def _getOrCreate(self, indexes):
        if indexes is None or (len(indexes)==1 and indexes[0] is None) or not len(indexes):
            return self

        #rebuild only the first one
        newmsg = self.getFunctionMsg().reIndex(tuple(indexes))

        for j in range(len(newmsg.keys)):
            i = newmsg.keys[j]
            ####
            # If the key has no index there is nothing to do
            ####
            if not i.hasIndex(): continue

            if self.value is None:
                self.value = {}

            if i.isIterable():
                ####
                # Just copy the actual iterable function but with a the new indexed msg
                ####
                return self._new( msg=newmsg )
            else:
                ####
                # freeze the curent key, it becomes not-iterable/no-index  anymore
                ####
                i  = FunctionKey(i.reform(), None)
                newmsg.keys[j] = i
                if not "%s"%i in self.value:
                    keypref = newmsg.keys[0:j+1]
                    ####
                    # To create a new iterabke function we need to be sure that all the keys
                    # above are in the raw form "KEYi"
                    ####
                    keyrest = [FunctionKeyi(s.key, None) if s.hasIndex() else s for s in newmsg.keys[j+1:None]]
                    tmpmsg = FunctionMsg.new( keypref+keyrest, newmsg.sep)


                    self.value["%s"%i] = self._new( msg=tmpmsg ,
                                                    value=None ,
                                                    onValueChange = self.onValueChange.derive(),
                                                    onSetup = self.onSetup.derive()
                    )
                self = self.value["%s"%i]
        return self


    def keys(self):
        if not self.isIterable():
            raise Exception("Function '%s' is not iterable"%self.msg)
        return self.msg.reformAll()



    def functions(self, default=False, onlyIfHasValue=True, errorIfNoLen=False):
        if onlyIfHasValue and not self.hasValue(default=default):
                return []

        if not self.isIterable():
            return [self]

        funcs = []

        for i,s in enumerate(self.msg.keys):
            if not s.hasIndex():
                continue

            ikey = s.index is None
            keys = self.value.keys() if ikey else s.reformAll()

            if ikey and errorIfNoLen and (not len(keys)):
                raise Exception("Cannot iter on '%s', it has no len"%s)

            for k in keys:
                sub = self[k]
                funcs.extend(sub.functions(onlyIfHasValue=onlyIfHasValue, default=default))
            break
        return funcs

        self._function( self, funcs, 0)
        return funcs

    def _function(self, sub , funcs, offset):
        if offset >= len(self.msg.keys):
            return
        s = self.msg.keys[offset]
        if not s.hasIndex():
            return self._function( sub, funcs, offset+1)


        keys = values.keys() if s.index is None else s.reformAll()
        for k in keys:
            self._function(sub[k] , funcs, offset+1)




    def getValue(self, value=None, default=False, context=None, index=None):
        """
        return the value if set (not None) else raise a ValueError

        Parameters
        ----------
        default (=False): return default value (if exists) if the value is not set.
        context (=None) : a context FunctionDict or dictionary instance with key/values
             pair. context is used the rebuild bracketed string value from the dictionary
             e.g. :  >>> f = Function( "DET FILE", "exop_{type}_{dit}.fits")
                     >>> f.getValue( context=dict(type="FLAT", dit=0.002))
        index (=None): index of returned value if function is iterable



        """

        self =  self._getOrCreate(index)

        if value is None and not self.hasValue(default):
            raise ValueError("'%s': no value set yet use default=True to get the default value instead, or .set(val) to set a value to this option or .new(val) to create a new one with value"%(self.getMsg()))

        if self.isIterable():
            if value is not None:
                raise ValueError("accept value only for non iterable Function")
            else:
                return {k:f.getValue(default=default, context=context) for k,f in self.value.iteritems() if f.hasValue()}

        if value is None:
            if self.value is None:
                return self.getDefault(context=context)
            value = self.value

        if context is not None:
            return self._rebuildVal(value, context)

        return value
    getV = getValue
    get  = getValue

    def getValueOrDefault(self, index=None):
        return self.getValue(default=True, index=index)
    getVod = getValueOrDefault

    def hasValue(self, default=False, index=None):
        self = self._getOrCreate(index)

        if self.isIterable():
            #if self.index and len(Self.index):
            #     pass

            return sum( f.hasValue() for f in self.value.values() )>0

        return self.value is not None or (default and self.hasDefault())

    def isDeletable(self, index=None):
        self = self._getOrCreate(index)
        if self.isIterable():
             return sum( f.isDeletable() for f in self.value.values() )==0
        return not self.hasValue()

    def cleanUp(self, index=None):
        self = self._getOrCreate(index)
        if not self.isIterable():
            return
        for k,f in self.value.iteritems():
            f.cleanUp()
        for k in self.value.keys():
            if self.value[k].isDeletable():
                del self.value[k]

    def select(self, id=True):
        self.selected = id
        self.onSelect.run(self)
    def unselect(self):
        self.selected = False
        self.onUnSelect.run(self)

    def isSelected(self, id=True):
        if id is True:
             return self.selected is not False
        return self.selected == id

    def selectUnselect(self, id=True):
        if self.isSelected(id):
             self.unselect()
        else:
             self.select(id)


    def hasDefault(self):
        return self.default is not None


    def setValue(self, value, index=None):
        self = self._getOrCreate(index)

        if self.isIterable():
            if value is None:
                self.value = {}
                return


            if not isinstance( value, dict):
                map( lambda f:f.setValue(value), self.functions(onlyIfHasValue=False, errorIfNoLen=True) )
                return

            for k,v in value.iteritems():
                #self._getOrCreate((k,))[self.index].setValue(v)
                self[k].setValue(v)
                #self._getOrCreate((k,)).setValue(v)
            return
        oldvalue = self.value
        self.value = self.parseValue(value)
        self.onValueChange.run(self, oldvalue)


    setV = setValue
    set  = setValue

    def setComment(self,comment):
        self.params['comment'] = str(comment)
    def getComment(self):
        return self.params.get('comment', "")
    def setDesciption(self, description):
        self.params['description'] = str(description)
    def getDescription(self):
        return self.params.get('description', "")
    def setUnit(self,unit):
        self.params['unit'] = str(unit)
    def getUnit(self):
        return self.params.get("unit","")
    def setContext(self,context):
        self.params["context"] = str(context)
    def getContext(self):
        return self.params.get("context")
    def setCls(self,cls):
        self.params["cls"] = list(cls or [] )
    def getCls(self):
        return self.params.get("cls",[])

    def setMsg(self, msg, sep=None):
        if isinstance(msg, str):
            msg = FunctionMsg(msg, sep=sep)
        elif not isinstance(msg, FunctionMsg):
            raise ValueError("expecting a str or FunctionMsg as message got %s"%type(msg))
        self.msg = msg

        #self.iterable = self._num_re.search(msg) is not None and self.index is None
        #self.iterable = len(self._num_re.findall(msg))
        #self.iterable = len( [s for s in self.msg.keys if s.isIterable()])
        #self.iterable = sum( [ True  for k in dotkey(msg).split(".") if self._num_re1.match(k) or self._num_reList1.match(k) or self._num_reSlice1.match(k)] )

    setM = setMsg

    def getFunctionMsg( self):
        return self.msg
        return FunctionMsg( dotkey(self.msg) )

    def getMsg(self, context=None, dot=True):
        if context is not None:
            msg = self.rebuildMsg(context, fromAttr=True)
        else:
            msg = self.msg.reform()

        if dot:
            msg = dotkey(msg)
        else:
            msg = undotkey(msg)

        return msg
    getM = getMsg

    def match(self, key, context=None, prefixOnly=False, partialy=True):
        return self.getFunctionMsg().match( key, prefixOnly=prefixOnly, partialy=partialy)

        msg  = dotkey(self.getMsg(context=context))
        msgs = msg.split(".")
        keys = dotkey(key).split(".")
        keyslen = len(keys)
        suffix = ""
        prefix = msg
        if prefixOnly:
            prefix = ".".join(msgs[0:keyslen])
            suffix = ".".join(msgs[keyslen:None])
            msgs   = msgs[0:keyslen]

        msgslen = len(msgs)

        if keyslen>msgslen: return None

        partialy = msgslen != keyslen
        indexes  = None
        if partialy:
            if keys[0] in msgs:
                s = msgs.index(keys[0])
                if keys == msgs[s:s+len(keys)]: return FunctionMatch(indexes,partialy, prefix, suffix)
        elif keys==msgs:
            return FunctionMatch(indexes,partialy, prefix, suffix)

        if self.isIterable():
            if partialy:
                for i in range(msgslen-keyslen+1):
                    m = self._matchIterable(msgs,  msgs[0:i]+keys+msgs[i+keyslen:None])
                    if m:  return FunctionMatch(m, partialy, prefix, suffix)

            else:
                m = self._matchIterable(msgs, keys)
                if m:  return FunctionMatch(m, partialy, prefix, suffix)
        return None

    _match_iter_num_re = re.compile("[0-9]+")
    @classmethod
    def _matchIterable(cls, ikeys, keys, prefix=False):
        """
        Look if the key is a iterable param  that match a numbered param
        e.g.  ["DET0","SUBWIN4"] should return a tuple index if this param is ["DETi", "SUBWINi"]
        """
        #ikeys = ikey.split(".")
        #keys  =  key.split(".")
        if prefix:
            ikeys = ikeys[0:len(keys)]
        elif len(ikeys)!=len(keys):
            return False

        idx = []

        for ikey,key in zip(ikeys,keys):
            res = cls._matchIterableOneKey(ikey, key)
            if res is False:
                return False
            if res is not -1:
                idx.append(res)
        return tuple(idx)


    @classmethod
    def _matchIterableOneKey(cls, ikey, key):
        pass
    @staticmethod
    def _savematchIterableOneKey(ikey, key):
        if ikey[-1] == "i":
            if key == ikey: # case of DETi == DETi
                return None

            if key == ikey[0:-1]: # case of index 0 e.i. DET0 is DET
                return 0

            if key[0:len(ikey)-1] == ikey[0:-1]:
                try:
                    i = int(key[len(ikey)-1:None])
                    return i
                except:
                    return False
            return False
        if ikey==key:
            return -1
        return False


    def isIterable(self):
        return self.getFunctionMsg().isIterable()

    def setDefault(self,default):
        if default is None and "default" in self.params:
            del self.params['default']
            return None
        self.params['default'] = self.parseValue(default)
    setD = setDefault

    def getDefault(self, default=None , context=None):
        if not "default" in self.params or self.params['default'] is None:
            if default is not None:
                return default
            else:
                raise ValueError("'%s' has no default value"%(self.getMsg()))

        if context is not None:
            return self._rebuildVal(self.params["default"], context)
        return self.params["default"]
    getD = getDefault


    def setFormat(self, fmt):
        if not issubclass( type(fmt), str) and not hasattr( fmt, "__call__"):
            raise ValueError("if format is not a string or tuple, should be a callable function or object ")
        self.params["format"] = fmt
    setF = setFormat

    def getFormat(self, tp=0):
        if tp>1 or tp<0:
            raise ValueError("type must be 0 for setup format or 1 for rebuilt format")
        fmt = self.params.get("format", "%s")
        if issubclass( type(fmt), tuple):
            return fmt[type]
        return fmt
    getF = getFormat

    def getDtype(self):
        return self.params.get("dtype", str)
    getT = getDtype
    def setDtype(self, dtype):
        if dtype is bool:
            dtype = vltbool
        self.params["dtype"] = dtype
    setT = setDtype

    def _cmdIterableWalker(self, dval, out , itr=[], context=None):
        if not isinstance( dval, dict):
            out += [(self.rebuildListMsg( tuple(itr)), self.formatValue(dval , context=context))]
            return None
        for k,v in dval.iteritems():
            self._cmdIterableWalker(v, out, itr+[k], context)

    @classmethod
    def _getAllIndexes(self, indexes):
        return self._getAllIndexesWalker( self.value, list(indexes))
    @classmethod
    def _getAllIndexesWalker( self, values, idx, shift=0):
        if shift == len(idx)-1:
            if idx[shift] is None:
                out = []
                for k in values:
                    idx[shift] = k
                    out += [tuple(idx)]
                return out
            return [tuple(idx)]

        idx = [i for i in idx]
        if idx[shift] is None:
            out = []
            for k in values:
                idx[shift] = k
                out += self._getAllIndexesWalker( values[k], idx, shift+1)
            return out

        return self._getAllIndexesWalker( values[idx[shift]], idx, shift+1)

    def todict( self, indexes=None, prefix=False, keyconvert=str, intkey=False):
        if not self.isIterable():
            raise Exception("This function is not iterable")

        msg = self.getMsg(dot=True)
        if isinstance(prefix, str):

             prefix = dotkey(prefix)
             if msg[0:len(prefix)] != prefix:
                  raise KeyError( "prefix '%s' do not match key '%s'"%(prefix,self.getMsg()))
             plen = len(prefix) +  (msg[len(prefix)] == ".")
        elif prefix is True:
             keys = msg.split(".")
             plen = 0
             for k in keys:
                  if self._num_re.match(k): break
                  plen += len(k)+1
        elif isinstance(prefix, int):
             plen = prefix
        else:
             plen = 0

        if indexes is None:
             indexes = self.value.keys()

        if isinstance(indexes, slice):
             indexes = range( indexes.start or min(self.value.keys()),
                              indexes.stop  or max(self.value.keys())+1,
                              indexes.step or 1
             )
        out = {}
        for i in indexes:
             f   = self[i]
             key = i if intkey else keyconvert(f.getMsg()[plen:None])
             out[key] = f
        return FunctionDict(out)

    def strKeyToIndex(self, key):
        if not self.isIterable():
            raise Exception("not iterable function")
        m = self.match(key)
        if m: return m.indexes
        raise KeyError("Cannot find index matching key '%s'"%key)



    def cmd(self, value=None, default=False, context=None):
        return cmd(map( lambda f: (f.getMsg(context=context),
                                  f.formatStripedValue(
                                  f.getValue(default=default) if value is None else value,
                                  context=context
                                  )
                              ),
                    self.functions(onlyIfHasValue=value is None)
        ))

    getCmd = cmd
    getC   = cmd

    def rebuildMsg( self, replacement=None, fromAttr=True):
        """
        msg = opt.rebuildMsg(replacement)

        if the message of the opt object is a string of the form "INS.OPT{optnumber}_"
        look for "optnumber" inside the replacement dict
        and replace {optnumber} by its value.
        Also the replacement patern can contain a format separated by a ',' : e.g.  "INS.OPT{optnumber,%04d}"
        Return the value of opt if it is not a string
        """
        if replacement is None:
            return self.msg.reform()

        if fromAttr:
            check = lambda k,r: hasattr(r,k)
            get   = lambda k,r: r.__getattribute__(k)
        else:
            check = lambda k,r: k in r
            get   = lambda k,r: r[k]


        strin   = self.msg.reform()
        matches = re.compile(r'[{]([^}]+)[}]').findall(strin)
        for key in matches:
            m = re.compile("[{]"+key+"[}]")
            f = m.search( strin)
            if f is not None: # shoudl not be
                start = strin[0:f.start()]
                end   = strin[f.end():None]

                sp = key.split(",")
                if len(sp)>1:
                    if len(sp)>2:
                        raise Exception("Error to reformat '%s' must contains only one pair of name,format")
                    fmt = sp[1]
                    key = sp[0]
                else:
                    fmt = "%s"

                if not check(key , replacement):
                    raise Exception("The replacement %s '%s' does not exists to rebuild '%s'"%("attribute" if fromAttr else "key", key,strin))
                val   = get(key, replacement)
                valp  = fmt%(val)
                strin = "%s%s%s"%(start, valp , end)

        return strin


    def rebuildVal( self, context, default=False):
        """
        val = f.rebuildVal(context, default=False)

        if the value of the Function object is a string of the form
        "TEST_{somekey}_" look for "somekey" inside context and replace
        {somekey} by its value.



        Return the value of the Function object  if it is not a string

        """
        return self._rebuildVal( self.get(default), context)

    @staticmethod
    def _rebuildVal(strin, context):
        if not issubclass(type(strin), str):
            return strin
        strout = ""
        for before, field, fmt, q in strin._formatter_parser():
            strout += before
            if field is None:
                continue
            field, others = field._formatter_field_name_split()

            for tp, name  in others:
                if tp:
                    field += ".%s" % name
                else:
                    break
            obj = context[field]

            for tp, name in others:
                if tp:
                    obj = getattr(obj, name)
                else:
                    obj = obj[name]



            if isinstance(obj, Function):
                strout += obj.__format__(fmt, context=context)
            else:
                strout += obj.__format__(fmt)

        return strout

    _matchekeys_re = re.compile(r'[{]([^}]+)[}]')
    @classmethod
    def _old_rebuildVal(cls, strin, fdict, default_replacement=True):

        if not issubclass(type(strin), str):
            return strin

        matches = cls._matchekeys_re.findall(strin)
        for key in matches:
            m = re.compile("[{]"+key+"[}]")
            f = m.search(strin)
            if f is not None: # shoudl not be
                start = strin[0:f.start()]
                end   = strin[f.end():None]

                sp = key.split(":")
                if len(sp)>1:
                    if len(sp)>2:
                        raise Exception("Error to reformat '%s' must contains only one pair of name,format"%sp)
                    fmt = "{:"+sp[1]+"}"
                    key = sp[0]
                else:
                    fmt = "{}"

                if not key in fdict:
                    raise Exception("The replacement key '%s' does not exists to rebuild '%s'"%(key,strin))

                val   = fdict[key]
                valp = fmt.format(val)

                strin = "%s%s%s"%(start, valp , end)
        return strin


    def getFormatedValue(self, value=None, default=False, context=None, index=None):
        self = self._getOrCreate(index)

        if self.isIterable():
            return {k:f.getFormatedValue(value=value, default=default, context=context) for k,f in self.value.iteritems() if f.hasValue()}
        return self.formatValue( self.getValue(value=value,default=default),  context=context)
    getFv = getFormatedValue

    def getFormatedValueOrDefault(self, value=None, context=None, index=None):
        return self.getFormatedValue(value=value, default=True, context=None, index=index)
    getFvod = getFormatedValueOrDefault

    def getFormatedDefault(self, *args, **kwargs):
        context = kwargs.pop("context", None)
        if len(kwargs):
            raise KeyError("getFormatedDefault accept only one keyword argument : 'replacement'")

        return self.formatValue(self.getDefault(*args), context=context)
    getFd = getFormatedDefault


    def _parse_walker(self, d):
        if isinstance( d , dict):
            return { k:self._parse_walker( subd) for k,subd in d.iteritems() }
        return self.getDtype()(d)

    def parseValue(self, value):
        # if the value is a list or any iterable and self is iterable e.i., msg containe '#'
        # like for instance DET.SUBWIN1.GEOMETRY, should parse individuals value in a list
        if hasattr( value, "__iter__"):
            if not self.isIterable():
                raise ValueError("got a iterable object but the option is not iterable")
            if isinstance( value, dict):
                return self._parse_walker(value)
                #return {k:self.getDtype()(v) for k,v in value.iteritems()}

            return [self.getDtype()(v) for v in value]
        if value is None:
            return None #a none value erase the previous value
        try:
            return self.getDtype()(value)
        except ValueError:
            raise ValueError("Cannot convert '%s' to the expecting type %s for param '%s'"%(value,self.getDtype(), self.getMsg()))

    def formatValue(self, value, context=None):
        if context is not None:
            value = self._rebuildVal( value, context)

        value = self.parseValue(value)
        return self._format(self.getFormat(0) , value)

    def formatStripedValue(self, value, context=None):
        return self.formatValue(value, context=context).strip()


    def setup(self, value=None, proc=None, **kwargs):
        if proc is None:
            proc = getDefaultProcess()
            if proc is None:
                raise Exception("not defaultProcess set in vlt module")
        #if not "setup" in self.cls:
        #    raise Exception("This function is not a setup class")

        out = proc.setup(function=self.cmd(value)+kwargs.pop("function",[]), **kwargs)
        self.onSetup.run(self)
        return out

    def status(self,proc=None, **kwargs):
        if proc is None:
            proc = getDefaultProcess()
            if proc is None:
                raise Exception("not defaultProcess set in vlt module")
        if self.statusFunc:
            msg = self.statusFunc.getMsg() if isinstance(self.statusFunc, Function) else self.statusFunc
        else:
            msg = self.getMsg()
        return proc.status(function=msg, **kwargs)

    def update(self, proc=None):
        res = self.status(proc)
        msg = self.getMsg()
        if not msg in res:
            raise Exception("weird, cannot find key '%s' in buffer result"%msg)
        self.setValue(res[msg])

    def updateDict(self, funclist, proc=None):
        res = self.status(proc)
        funclist.update( res )
    def getOrUpdate( self, proc=None):
        if self.hasValue():
            return self.get()
        self.update(proc=proc)
        return self.get()

    def updateAndGet(self, proc=None):
        self.update(proc=proc)
        return self.get()


    @staticmethod
    def _format(fmt,value):
        if issubclass( type(fmt), str):
            # format can be a string or a function
            return fmt%(value)
        else:
            return fmt(value)





def getItemShape(items):
     return [ len(i) if hasattr(i,"__len__") and hasattr(i,"__iter__") else 0 for i in items ]

def sliceToRange( items):
     return tuple( range(i.start,i.stop, i.step or 1) if isinstance(i,slice) else i for i in items )

def itemExplode(items):

     items = sliceToRange(items)
     shape = getItemShape(items)
     itemlen = len(shape)
     if not sum(shape): return items
     N = 1
     for s in shape: N *= s if s else 1

     out = []
     for i in range(N):
          tmp = []
          for j in range(itemlen):
               if shape[j]:
                    tmp.append( items[j][i%shape[j]] )
               else:
                    tmp.append( items[j] )
          out.append( tuple(tmp))
     return out


class FunctionIter:
    def __init__(self, function):
        self.function = function
        self.indexes = function._getAllIndexes()
        self.counter = -1
        self.size = len( self.indexes)
    def next(self):
        self.counter += 1
        if self.counter >= self.size:
            raise StopIteration("out of range")
        return self.function[self.indexes[self.counter]]



def remove_dict_prefix(din, prefix, err=False):

    plen = len(prefix)

    for k, v in din.items(): # do not use iteritems here
        if not isinstance(k,str): continue
        if k[0:plen] == prefix:
            newk = k[plen:None].strip(". ")
            if not newk in din:
                din.pop(k)
                din[newk] = v
            elif err:
                raise KeyError("key '%s' already exists"%newk)
        elif err:
            raise KeyError("cannot match prefix '%s' in key '%s'"%(prefix, k))

def merge_function_dict(left, right):

    trueKey = (bool(left._prefix) or bool(right._prefix)) and (left._prefix!=right._prefix)

    left  = left.copy( trueKey=trueKey)
    right = right.copy(trueKey=trueKey)

    left.update(right)
    if trueKey:
        left._prefix = None

    return left


def functionlist(*args):
    fd = FunctionDict()
    fd.add(*args)
    return fd

class EmbigousKey(KeyError):
    pass

class FunctionDict(dict):
    keySensitive  = False
    dotSensitive  = False
    noDuplicate   = False

    _child_object = Function
    _prefix = None
    proc    = None
    statusKeys = None
    def __init__(self, *args, **kwargs):
        super(FunctionDict,self).__init__(*args, **kwargs)
        for k, opt in self.iteritems():
            if not issubclass( type(opt), self._child_object):
                raise ValueError("All element of %s must be a subclass of %s"%(self.__class__, self._child_object))
            if self.noDuplicate:
                dup = self._checkduplicate(k, opt)
                if dup:
                    raise ValueError("Duplicate not permited. The parameter '%s' already exists under the key '%s' for message '%s'"%(k, dup, self[dup].getMsg()))

        self.onSetup  = Actions()
        self.onUpdate = Actions()

    def __call__(self, preforlist):
        out = self.restrict( preforlist )
        if len(out)==1:
            return out['']
        return out

    def __getitem__(self,item):

        if issubclass(type(item), tuple):
            if len(item)>2:
                raise IndexError("axcept no more than two items, second item should be a string")

            if len(item)>1:
                attr_key = [item[1]]
            else:
                # case of  f[key,] by default this is "value"
                attr_key =  "value"
            attr = "get"+attr_key.capitalize()
            out = self[item[0]]
            if not hasattr(out, attr):
                raise AttributeError("method %s does not exists for obj of class"%(attr, out.__class__))
            out = getattr(out, attr)

            if isinstance(out, dict) and self._prefix:
                out.setPrefix(self._prefix)
            if isinstance( out, FunctionDict):
                self._copy_attr(out)
            return out

        if not item in self:
            raise KeyError("item '%s' does not exists for the FunctionDict"%item)

        return self.get(item)


    def __setitem__(self,item, val):
        """ d[item] = val
            see method .setitem for more help
        """
        # setitem understand what to do function to the value
        # if value is a self._child_object it will be set like on a dictionary
        # else try to set the value inside the _child_object, if that case if the key does not
        # exists raise a KeyError

        if issubclass(type(item), tuple):
            if len(item)>2:
                raise IndexError("axcept no more than to items, second item should be a string")

            if len(item)>1:
                self[item[0]][item[1]] = val
                return None
            else:
                # case of  f[key,] by default this is "value"
                self[item[0]]["value"] = val
                return None

        return self.setitem(item, val)


    def __contains__(self,item):
        if super(FunctionDict, self).__contains__(item):
            return True


        keys = FunctionMsg(dotkey(item))
        for f in self.itervalues():
            if f.match(keys):
                return True
        if False and self._prefix:
            item = "%s.%s"%(self._prefix,keys)
            for f in self.itervalues():
                if f.match(keys):
                    return True
        return False

    def key(self,item):
        if super(FunctionDict, self).__contains__(item):
            return item #key is the item

        keys = FunctionMsg(dotkey(item))
        for k,f in self.iteritems():
            if f.match(keys):
                ########
                # Check if self[k] is the same than self[item]
                # because, e.g. DET.DIT can match DETi.DIT but are not
                # the same output
                if self[k]==self[item]: return k
                return item
        if False and self._prefix:
            item = "%s.%s"%(self._prefix,keys)
            for k,f in self.iteritems():
                if f.match(keys):
                    if self[k]==self[item]: return k
                    return item
        return None


    def __radd__(self, left):
        return merge_function_dict(self,left)
        return self.__class__(left.copy().items()+self.copy().items())
    def __add__(self, right):
        return merge_function_dict(right, self)
        return self.__class__(self.copy().items()+right.copy().items())

    def __format__(self, format_spec):
        if not len(format_spec):
            format_spec = "s"
        if format_spec[-1] != "s":
            raise Exception("FunctionDict accept only 's' formater ")
        return cmd2str(self.rcopy().cmd())



    def getProc(self, proc=None):
        try:
            return proc if proc is not None else getProc(self.proc)
        except:
            raise Exception("No default process in the FunctionDict neither in the VLT module")

    def setProc(self, proc):
        if not isinstance(proc, Process):
            raise ValueError("Expecting a procees object")
        self.proc = proc


    def getSelected(self, id=True):
        out = {k:f for k,f in self.iteritems() if f.isSelected(id)}
        return self._copy_attr(self.__class__(out))
    def getUnSelected(self, id=True):
        out = {k:f for k,f in self.iteritems() if not f.isSelected(id)}
        return self._copy_attr(self.__class__(out))
    def selectAll(self, id=True):
        for f in self.itervalues():
             f.select(id)
    def unselectAll(self):
        for f in self.itervalues():
             f.unselect()

    def setPrefix(self, prefix):
        """ To be droped """
        remove_dict_prefix(self, prefix, True)
        self._prefix = prefix

    def restrict(self, preforlist):
        """
        restrict the FunctionDict to mathed items.
        the unique argument can be
        - a string in this case the returned dictionary will be restricted
          to all Function with a key starting by the string
          e.g.:

            d = vlt.functionlist( "INS1.OPT1.NAME grism", "INS1.OPT1.ENC 1200",
                                  "INS1.OPT2.NAME grism", "INS1.OPT2.ENC 800")


            restricted = d.restrict("INS1.OPT1")
            return a dictionary with only the element starting by "INS1.OPT1"
            The "INS1.OPT1" will be dropped in the return dictionary.
            So restricted["NAME"] will work but conveniently
            restricted["INS1.OPT1.NAME"] will work as well

        - a list of string keys:
            the returned FunctionDict will be restricted to the matched keys


        SEE ALSO:
        ---------
        restrictClass, restrictContext, restrictValue, restrictHasValue,
        restrictHasNoValue
        """
        if issubclass( type(preforlist), str):
            pref = dotkey(preforlist)
            out = {}

            for k,f in self.iteritems():
                m = f.match(pref, prefixOnly=True)
                if m:
                    nf = f[m.indexes] if m.indexes else f
                    out[m.suffix] = nf

            if self._prefix: # try the same with prefix
                pref = dotkey("%s.%s"%(self._prefix,preforlist))
                m = f.match(pref, prefixOnly=True)
                if m:
                    nf = f[m.indexes] if m.indexes else f
                    out[m.suffix] = nf

            out = self._copy_attr(self.__class__(out))
            out._prefix = (self._prefix+"." if self._prefix else "")+preforlist
            return out

        lst  = preforlist
        keys = [k if isinstance(k,tuple) else (k,k) for k in lst]

        return self._copy_attr(self.__class__({ka:self[k] for k,ka in keys}))

    def restrictParam(self, params, getmethod, test):
        if not isinstance(params , (list,tuple)):
            params = [params]
        out = {}
        for k,f in self.iteritems():
            for p in params:
                if test( p,getmethod(f)):
                    out[k] = f
                    continue
        return self._copy_attr( self.__class__(out))
    def restrictClass( self, cls):
        """ return a restricted FunctionDict of Function of 'class' cls
        cls can be a string or a list of string
        """
        return self.restrictParam(cls, self._child_object.getCls, lambda p,l:p in l)

    def restrictContext( self, context):
        """ return a restricted FunctionDict of Function of 'context' context
        context can be a string or a list of string
        """
        return self.restrictParam(context, self._child_object.getContext, lambda p,l: p==l)

    def restrictValue(self, value):
        """ return a restricted FunctionDict of Function with value """
        return self.restrictHasValue().restrictParam([value],
                                                     self._child_object.getValue,
                                                     lambda p,l: p==l)

    def restrictHasValue(self):
        """ Return a FunctionDict with the child Function that have a
        defined value only """
        return self.restrict([k for k,f in self.iteritems() if f .hasValue()])

    def restrictHasNoValue(self):
        """ Return a FunctionDict with the child Function that have *NO*
        defined value"""
        return self.restrict([k for k,f in self.iteritems() if not f .hasValue()])

    def restrictMatch(self, pattern):
        """ Reutnr a FunctionDict restricted to mathed Key Function
         e.g.:  restrictedMatch( "NAME")
          will return a FunctionDict containing the "NAME" key like
             for instance  "INS1.FILT1.NAME"
        """
        return self.restrict([k for k,f in self.iteritems() if not f .match(pattern)])


    def has_key(self,key):
        return key in self


    def add(self, *args):
        """
        add item to the dictionary. Item should be a Function object or
        a string or a tuple.
        if string or tuple, it is converted to a Function object by
        Function.newFromCmd(item)

        The dictionary key/msg will be the key of the Function, returned by
        Function.getMsg()

        e.g:

        d.add( "INS1.OPT1.ENCREL 2400", Function("DET.DIT", 0.0001),
               ("DET.NDIT", 1000), .....
              )

        """
        for arg in args:
            if isinstance(arg, (tuple,basestring)):
                arg = Function.newFromCmd(arg)
            if not isinstance(arg, self._child_object):
                raise TypeError("argument should be tuple or Function, got %s" % arg)
            super(FunctionDict, self).__setitem__(arg.getMsg(), arg)

    def setitem(self, item, val):
        """
        setitem(item, opt_or_value)
        set a item in the FunctionDict,
        The first argument is a key string the second a value to set

        If the key already exists in the FunctionDict the value can be both
        a new Function object (will replace) or a value (str,int, etc ...) in
        this case the value is set in the coresponding Function.

        If the key does not exists, it accept only a Function object or a tuple
        (key,val) wich will be converted to a Function

        d.setitem(key,val) is iddentical to d[key] = val


        However one can set a value in the item only if the item already exists
        optdict.setitem(item, opt) is strictely equivalent to optdict[item] = opt

        e.g. :
           d = FunctionDict( dit=Function("DET.DIT", float) )

           d['dit']     = Function("DET.DIT", float)  #will work
           d['dit']     = 0.001 #will work
           d['DET.DIT'] = 0.001 #will work
           d['dummy']    = 10 #ERROR dummy does not exists
           d['dummy']    = Function("DET.DUMMY", int)  #will work

        """
        if isinstance(val, tuple):
            val = Function.newFromCmd(val)

        if not KEY_MATCH_CASE:
            item = upperKey(item)


        if issubclass(type(val), self._child_object):
            if self.noDuplicate:
                dup = self._checkduplicate(item, val)
                if dup:
                    raise ValueError("Duplicate not authorized. The parameter already exists under the key '%s' for message '%s'"%(dup, self[dup].getMsg()))
            super(FunctionDict, self).__setitem__(item, val)
            return None
        if not item in self:
            ikey = self.getIterableKeyLike(item)
            if ikey[0] in self:
                return self[ikey[0]][ikey[1]].setValue(val)

            raise KeyError("Element '%s' does not exist. Cannot set a none %s object if the item does not exists"%(item,self._child_object))
        return self[item].setValue(val)

    _match_iter_num_re = re.compile("[0-9]+")
    def getIterableKeyLike(self, key):

        ikey    = self._match_iter_num_re.sub( "i", key)
        indexes = tuple([int(m) for m in self._match_iter_num_re.findall(key)])
        return (ikey, indexes)
    def hasIterableKeyLike( self, key):
        """
        Look if can find a iterable param  that match a numbered param
        e.g.  "DET0 SUBWIN4" should return True if "DETi SUBWINi" exists
        """
        return self.getIterableKeyLike(key)[0] in self

    def update(self, *args, **kwargs):
        if len(args)>1:
            raise ValueError("update accept only one optional positional argument")

        if len(args):
            a0 = dict(args[0])  if issubclass( type(args[0]), list) else args[0]

            for k,a in a0.iteritems():
                self[k] = a
        for k,a in kwargs.iteritems():
            self[k] = a

    def set(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self

    def get(self, item, default=None):
        if default is not None and not issubclass(type(default), self._child_object):
            raise ValueError( "default should be None or a %s object "%self._child_object)

        if super(FunctionDict, self).__contains__(item):
            return super(FunctionDict, self).get(item, default)
        if not KEY_MATCH_CASE:
            uitem = upperKey(item)
            if super(FunctionDict, self).__contains__(uitem):
                return super(FunctionDict, self).get(uitem, default)

        fout = None
        for f in self.values():
            m = f.match(item)
            if m:
                if fout:# and fout.match(item):
                    if m.partialy:
                        raise EmbigousKey("Embigous key '%s'"%item)
                fout = f[m.indexes] if m.indexes else f
                if not m.partialy: break #no embiguity stop here
        if fout:return fout


        if self._prefix:
            item = "%s.%s"%(self._prefix,item)
            for f in self.values():
                m = f.match(item)
                if m:
                    if fout:
                        raise EmbigousKey("Embigous key '%s'"%item)
                    fout = f[m.indexes] if m.indexes else f
                    if not m.partialy: break #no embiguity stop here
        if fout:return fout

        return default

    def _status(self, keylist=None, proc=None):
        keylist = keylist or []
        return self.getProc(proc).status(function=keylist)

    _spacereg = re.compile("[ ]+")
    def status(self, keylist=None, proc=None, indict=False):
        """ status return a dictionary of key/value pairs sent and return from the process
        keyword are:
            keylist= - A restrictive list of key or a string where keys are space separated
                     - if keylist is None, use the statusKeys attribute,
                           if also None the status process is called without argument
                     - if keylist is False  use all the dictionary keys!!

            proc= is the Process, if is None use the default one if exists
            indict = if True Return results in a python dictionary else in a FunctionDict
        """
        if keylist is None:
            keylist = self.statusKeys

        if isinstance(keylist, str):
            keylist = self._spacereg.split(keylist)
        if keylist is False:
             keylist = None
        elif keylist is None:
             keylist = self.keys()

        if keylist:
            keylist = [self[k].getMsg() for k in keylist]
        st = self.getProc(proc).status(function=keylist)
        valdict = st


        if indict:
            return valdict
        return self.dict2func(valdict)

    def dict2func(self, dictval):
        output = FunctionDict()
        for k,v in dictval.iteritems():
            ks = self.key(k)
            if ks:
                f = self[ks].copy()
                f.set(v)
                output[ks] = f
            else:
                output[k] = Function(k,v)
        return self._copy_attr(output)

    def statusUpdate(self, keylist=None, proc=None):
        """
        update the disctionary function values from the Process.
        statusUpdate return a Function dictionary containing all the updated Functions

        keylist= - A restrictive list of key or a string where keys are space separated
          - if keylist is None, use the statusKeys attribute,
                if also None the status process is called without argument
          - if keylist is False  use all the dictionary keys!!

        proc= is the Process, if is None use the default one
        """
        vals = self.status(keylist, proc=proc, indict=True)
        setkeys = []
        for k,v in vals.iteritems():
            if k in self:

                self[k].setValue(v)
                setkeys.append(k)

        self.onUpdate.run(self)
        return self.restrict(setkeys)


    def _checkduplicate(self, key, opt):
        """
        check if there is any duplicates Function inside the dictionary
        return the key if one is found.
        """
        optmsg = opt.getMsg()
        for k,f in self.iteritems():
            if k!=key and optmsg == f.getMsg():
                return k
        return ""

    def _copy_attr(self, new):
        """
        Internal function to copy parameters from one object instance to an other
        """
        new.proc     = self.proc
        new.onSetup  = self.onSetup
        new.onUpdate = self.onUpdate
        new._prefix  = self._prefix
        return new

    def setAliases(self, aliases):
        if isinstance( aliases, list): aliases = dict(aliases)
        for k,alias in aliases.iteritems():
            self[alias] = self[k]

    def copyWithAliases(self, aliases, deep=False):
        new = self.copy(deep=deep)
        new.setAliases(aliases)
        return new

    def copy(self, deep=False, trueKey=False):
        if trueKey:
            if deep:
                new = {f.getMsg():f.copy(True) for f in self.itervalues()}
            else:
                new = {f.getMsg():f for f in self.itervalues()}

        else:
            if deep:
                new = {k:f.copy(True) for k,f in self.iteritems()}
            else:
                new = super(FunctionDict, self).copy()

        return self._copy_attr(self.__class__(new))

    def rcopy(self, deep=False, default=False):
        """
        Return a restricted copy of a Function dictionary with only the Function
        that have a value set.
        2 keywords:
            - deep    : if True make a copy of each Function inside the directory
            - default : if True return also Function that have a default value
        """
        if deep:
            return self._copy_attr( self.__class__({k:f.copy() for k,f in self.iteritems() if f.hasValue(default=default)}))

        return self._copy_attr( self.__class__({k:f for k,f in self.iteritems() if f.hasValue(default=default)}))


    def msgs(self, context=None):
        """
        return the list of keys message (as passed to a process)
        """
        return [f.getMsg(context=context) for f in self.values()]

    def todict(self, default=False):
        """
        Parameters
        ----------
        default (=False) : True/False use/no use default if value is not set
        Returns
        -------
        return a dictionary of key/value pair for all function with a value set
        """
        return {k:f.get(default=default) for k,f in self.iteritems() if f.hasValue(default=default)}

    def toalldict(self, default=False, context=None):
        return {k:self[k].get(default=default) for k in set( self.keys()+self.msgs(context=context))}


    def tocmd( self, values=None, withvalue=True, default=False,
              context=None, contextdefault=True):
        """
        get a list of command with key/value pairs ready to be passed to
        a process function

        Parameters
        ----------
        values  (={})    : A key/value dictionary to be parsed without changing
                           Values set inside dicitonary
        withvalue (=True):  If True, add the command pair to all the child Function
                            in this FunctionDict that has a value defined
                            other whise setup only the Function in the input values
                            dictionary.
        default (=False) : True/False use/no use default if value is not set
        proc    (=None)  : Process to use instead of the default one if any
        context (=None)  : The context keyword is a FunctionDict, System, Device or
             a dict (key/value pair)object. It is used to replace bracketed
             string value to the coresponding value found in context.
             For instance "{type}" will be replaced by the value context["type"].
             Also the bracketed key replacement can be formated : "{nexpo:03d}",
             it will overwrite the default format of "nexpo"
             If context is None (default) it will use the own functionDict as context so:
             fd.tocmd(context=fd) is equivalent to fd.tocmd()
             If context is False no context is used, bracket keys (if any) are left as
             it is.

        contextdefault (=True) : True/False control if default values are used for
             the context replacement if no values has been set

        Returns
        -------
        List of (key,string value) pair ready to be passed in setup process

        Examples:
        --------

        >>> fd = FunctionDict(type = Function("TYPE", value="test"),
                              file = Function("FILE", value="result_{type}_{det:2.3f}.data"),
                              det = Function("DET", value=0.1)
                              )
        >>> fd.tocmd(context=fd)
        [('DET', '0.1'), ('TYPE', 'test'), ('FILE', 'result_test_0.100.data')]

        """
        values = values or {}
        if context is None:
            # make a deep copy and set the new values in context
            context = self.copy(True)
            for k,f in values.iteritems():
                context[k] = f

        elif context is False:
            context = None


        out = []
        funcs = []
        for k in values:
            f = self[k]
            if not f in funcs:
                out.extend(f.cmd(value=values.get(k),
                           default=default, context=context)
                          )
            funcs.append(f)
        if withvalue:
            for k,f in self.iteritems():
                if f.hasValue(default):
                    if not f in funcs:
                        out.extend(f.cmd(default=default,context=context))

        return out
    cmd = tocmd

    def qcmd(self, _values_=None, **kwargs):
        values = _values_ or {}
        values.update(kwargs)
        return self.cmd(values, False)

    def setup(self, values=None, withvalue=True, default=False, context=None,
              contextdefault=True, proc=None, **kwargs):
        """
        Send a Setup from all the function with a value (or default set if default=True)

        Parameters
        ----------

          values  (=None)  :  a dictionary of key:value pairs all keys must
                              match any of the FunctionDict Child Function
          withvalue (=True):  If True, add the setup command to all the function
                              in this FunctionDict that has a value defined
                              other whise setup only the Function in the values
                              dictionary.
          proc    (=None)  :  Process to use instead of the default one
          context (=None)  :  bracketed string value replacement (see the tocmd help)
          contextdefault (=True) : use/not use default for context replacement
          function: (=[]) : a list of function pair to add to the setup.

        All others kwargs are passed to the setup function process,
        they are usualy (but depend on the instrument SETUP command):
        expoId, noMove, check, noExposure, function

        Returns
        -------
        The process setup tuple output

        See Also
        --------
        qsetup method for a more user friendly way to setup

        """
        cmdfunc = self.tocmd(values=values, withvalue=withvalue,
                             default=default, context=context,
                             contextdefault=contextdefault)

        cmdfunc = cmdfunc+kwargs.pop("function",[])

        out = self.getProc(proc).setup(function=cmdfunc, **kwargs)

        self.onSetup.run(self)
        return out

    def qsetup(self, _values_=None, **kwargs):
        """ qsetup stand for quick setup

        qsetup( dit=0.01, ndit = 1000, expoId=0, timeout=1000)
        is equivalent to:
        setup( {"DIT":0.01, "NDIT":1000}, expoId=0, timeout=1000)

        If the keyword exist in the FunctionDict it is used at it is
        otherwhise try with an upper case keyword.

        qsetup accept also a positional dictionary argument (like setup) to
        parse none python like symbols.

        Note that qsetup send the setup for only the qeywords provided in
        the function call (e.i.: withvalue=False in setup function)

        e.g.:
        > d.qsetup( dit=0.001, ndit=1000 )
        can also be decomposed:
        > d["DIT"] = 0.001
        > d["NDIT"] = 1000
        > d.setup()

        """
        proc = self.getProc(None)
        # Remove all the option for the setup command
        pkeys = proc.commands["setup"].options.keys()+["timeout"]
        pkwargs = {k:kwargs.pop(k) for k in kwargs.keys() if k in pkeys}

        cmdfunc = self.qcmd(_values_, **kwargs)+pkwargs.pop("function",[])

        out = self.getProc(proc).setup(function=cmdfunc, **pkwargs)

        self.onSetup.run(self)
        return out





def cmd2Option(msg,fromdict=None):
    return Function.newFromCmd(msg, fromdict=fromdict)

def cmd2Function(msg, fromdict=None):
    return Function.newFromCmd(msg, fromdict=fromdict)

def dotkey(key):
    return ".".join( key.split(" ") )
def undotkey(key):
    return ".".join( key.split(" ") )


class Param(Option):
    """
    Samething than Option except that if the value is None,
    an empty string is return from the function cmd()
    """
    def cmd(self,value):
        if value is None:
            return ""
        return "%s %s"%(self.msg, self.formatValue(value))

class Command(object):
    options  = {}
    helpText = ""
    _debugBuffer = None
    def __init__(self, msg, options, helpText="", bufferReader=None):
        self.msg = msg
        self.options = options
        self.helpText = helpText
        self.bufferReader = bufferReader

    def cmd(self, kwargs):
        for k,opt in self.options.iteritems():
            kwargs.setdefault(k, opt.default)
        cmds = []
        for k,value in kwargs.iteritems():
            if not k in self.options:
                raise KeyError("The option '%s' is unknown for command %s"%(k,self.msg))
            ## ignore the value None
            opt    = self.options[k]
            cmdstr = opt.cmd(value)
            if cmdstr.strip():
                cmds.append(cmdstr)
        return """%s \"%s\""""%(self.msg, " ".join(cmds))

    def readBuffer(self, buff):
        if self.bufferReader is None:
            return buff
        return self.bufferReader(buff)
    def getDebugBuffer(self):
        return self._debugBuffer
    def setDebugBuffer(self, buf):
        self._debugBuffer= buf

    def status(self):
        return self.proc.status()



def processClass(processname, path=None):
    """
    Return the dynamicaly created python class of a process

    The program look for the file processname.cdt into the list of path
    directories wich can be set by the path= keyword.
    By default config["cdtpath"] is used
    """
    import cdt
    fileName = cdt.findCdtFile(processname+".cdt", path)
    pycode = cdt.Cdt(fileName).parse2pycode()

    exec pycode
    # the pycode should contain the variable proc
    # witch is the newly created object
    return cls

def openProcess(processname, path=None):
    """
    return processClass(processname, path)()

    e.g.:
      pnoc = openProcess("pnoControl")
      pnoc.setup( function="INS.MODE ENGENIERING DET.DIT 0.01" )

    """
    return processClass(processname, path)()

    # pyfile = cdt.Cdt(fileName).parse2pyfile()
    #
    # mod = __import__("vlt.processes."+processname,
    #                  fromlist=[processname])
    # reload(mod) #in case cdt changed
    # return mod.proc




def vltbool(val):
    return bool( val!='F' and val!=False and val)


def parameter2function(param):
    if param['type'] is bool:
        param["format"] = formatBoolFunction
        param['type'] = vltbool

    return Function(param['name'],
                    dtype=param['type'],
                    format=param.get("format", "%s"),
                    default=None, value=None, index=None,
                    comment=param.get("comment", "%s"),
                    description=param.get("description", ""),
                    unit=param.get("unit", ""),
                    context=param.get("context", ""),
                    cls=param.get("class", "").split("|"))

def parameterDictionary2functionDict( pdictionary):
    out = FunctionDict()
    for k,p in pdictionary.iteritems():
        out[k] = parameter2function(p)
    return out

def readDictionary(dictFileSufix, path=None):
    import dictionary
    dfileName = dictionary.findDictionaryFile(dictFileSufix, path)
    dfile = dictionary.Dictionary(dfileName)
    dfile.parse()
    return parameterDictionary2functionDict( dfile.dictionary)


def _addProcess(processname):
    """
    *Deprecated*
     Check the processes/__init__.py file and add an "import processname" in it
    """
    import processes as procs

    fproc =  open(os.path.dirname( procs.__file__ )+"/__init__.py", "a+")
    l = fproc.readline()

    check = False
    while l!='':
        if re.compile("import[ ]+(%s)"%(processname)).search(l) is not None:
            check = True
            break
        l = fproc.readline()

    if not check:
        fproc.write("\nimport %s"%processname)
        reload(procs)
    fproc.close()

class VLTError(Exception):
    pass

class Process(object):
    commands = {}
    _debug   = debug
    _debugBuffer = None
    _verbose = verbose
    msg = ""

    def __init__(self, msg=None, commands=None, doubleQuote=False):
        commands = commands or {}

        for k,cmd in commands.iteritems():
            if not issubclass(type(cmd), Command):
                raise TypeError("expecting a Command object got %s for key '%s'"%(type(cmd), k))
            self.commands[k] = cmd

        if msg is not None:
            self.msg = msg
        self.doubleQuote = doubleQuote
        self.msgSend_cmd = msgSend_cmd
    def setVerbose(self, val):
        self._verbose = int(verbose)
    def setDebug(self,value):
        self._debug = bool(value)

    def getDebug(self):
        return self._debug
    def getVerbose(self):
        return self._verbose

    def cmd(self, command, options=None, timeout=DEFAULT_TIMEOUT):
        options = options or {}
        if not command in self.commands:
            raise KeyError("command '%s' does not exists for this process"%(command))
        cmd = self.commands[command]
        return _timeout_( "%s %s"%(self.msg, cmd.cmd(options)), timeout)

    def cmdMsgSend(self, command, options=None, timeout=DEFAULT_TIMEOUT):
        options = options or {}
        return _timeout_("""%s "" %s"""%(self.msgSend_cmd, self.cmd(command,options)), timeout)

    def msgSend(self, command, options=None, timeout=DEFAULT_TIMEOUT):
        global LASTBUFFER
        options = options or {}
        cmdLine = self.cmdMsgSend(command, options, timeout=timeout)
        if self.getVerbose():
            print cmdLine

        if self.getDebug():

            buf = self.commands[command].getDebugBuffer() or "MESSAGEBUFFER:\n"
            objout = self.commands[command].readBuffer(buf)
            LASTBUFFER = "DEBUG: %s"%(cmdLine)
            return objout

        status, output = commands.getstatusoutput(cmdLine)
        if status:
            raise VLTError("msgSend reseived error %d"%status)

        LASTBUFFER = output
        objOutput = self.commands[command].readBuffer(output)
        return objOutput


    def help(self,command=None):
        if command is None:
            for c in self.commands:
                self.help(c)
            return

        if not command in self.commands:
            raise KeyError("command '%s' does not exists for this process"%(command))
        opts = ", ".join( "{}={}".format(k,o.dtype) for k,o in self.commands[command].options.iteritems())
        print "-"*60
        print "{}({})".format(command, opts)
        print self.commands[command].helpText
    def getCommandList(self):
        return self.commands.keys()

def _timeout_(cmd, timeout):
    """
    just return the command cmd with the timeout attahced if any
    """
    if timeout:
        return "%s %d"%(cmd,timeout)
    return cmd




class SendCommand(Process):
    msg_cmd = "pndcomSendCommand"
    def cmdMsgSend(self, command, options=None, timeout=None):
        options = options or {}
        return """%s %s"""%(self.msg_cmd, self.cmd(command,options))


class Cmd(list):
    def __add__(self, right):
        return cmds(self, right)

    def __addr__(self, left):
        return cmds(left, self)

def cmd(st):
    """
    From a string or list or list of tuple return a flat list of valid
    command frunction/key pair

    > cmd(  ("DET.DIT", 0.003) )
    [('DET', 'DIT')]
    > cmd( [ ("DET.DIT",0.001), [[("DET.NDIT",100)]]] )
    [('DET.DIT', 0.001), ('DET.NDIT', 100)]
    """
    if issubclass(type(st), (list)):
        # Always return a flat list
        cmds = []
        for c in st:
            cmds += cmd(c)
        return Cmd(cmds)
    #this is always a flat list
    return Cmd([st])

def cmd2str(tcmd):
    tcmd = cmd(tcmd) # make a flat list

    out  = []
    for c,v in tcmd:
        if isinstance(v, str) and v.find(" ")>-1:
            v = "'{}'".format(v)
        out.append( "{} {}".format(c,v))
    return " ".join(out)

def cmds(*args):
    output = []
    for a in args:
        output += cmd(a)
    #
    # Return the list and elimiminate duplicate
    return Cmd(dict(output).items())


class Params(dict):
    def __init__(self, *args, **kwargs):
        super(Params,self).__init__(*args, **kwargs)
        for p,v in self.iteritems():
            if not issubclass(type(v),Param):
                raise TypeError("Params Accept only Param type got %s"%(type(v)))


class System(object):
    # a list of function of the system
    # e.g. for a detector
    #    functions = {
    #             'dit'  :Function("DET.DIT"  , float, "%f", 0.0 ),
    #             'ndit' :Function("DET.NDIT" ,  long, "%d", 10  ),
    #             'polar':Function("DET.POLAR", int , "%04d", 0),
    #
    #             'type':Function( "DPR.TYPE", str , "%s", "TEST" ),
    #             'tech':Function( "DPR.TECH", str , "%s", "image"),
    #             'imgname':Function( "OCS.DET.IMGNAME", str , "%s", "IMG_{type}"),
    #
    #             'mode':Function( "INS.MODE", str , "%s", "ENGINEERING" ),
    #             'readoutmode':Function("INS.READOUT.MODE", str , "%s", "DOUBLE")
    #         }
    functions = FunctionDict({})
    # a list of mendatory functions for instance "INS.MODE"

    # a list of function for wich the value should be rebuild from others function
    # for instance rebuild = ["type","imgname"] , order matter
    # type and then imgname will be rebuilt if e.g.
    #  type = "BIAS-{polar}"  # {polar} will be replaced by the value of polar
    #  imgname = "INSTRUMENT-{type}_" # {type} will be replaced by the previously rebuilt type
    rebuild = []
    module  = True
    counter = 0
    def __init__(self, proc):
        self.proc = proc

    def __setitem__( self, item, value):
        # set the item in the self.function
        self.functions[item] = value
    def __getitem__( self, item):
        # return the item inside the functiondic
        return self.functions[item]
    def __iter__(self):
        # return the functionsDict as iterator
        return self.functions.__iter__()
    def __contains__(self, item):
        # return the functionsDict as iterator
        return self.functions.__contains__(item)
    def __format__(self, fmt_spec):
        # return the functionsDict as iterator
        return self.functions.__format__(fmt_spec)
    def copy(self):
        new = self.__class__(self.proc)
        new.functions = self.functions.copy(True)
        return new

    def iteritems(self):
        return self.functions.iteritems()
    def iterkeys(self):
        return self.functions.iterkeys()
    def items(self):
        return self.functions.items()
    def keys(self):
        return self.functions.keys()
    def pop(self, *args):
        return self.functions.pop(*args)
    def setdefault(self, *args):
        return self.functions.setdefault(*args)


    def new(self, *args, **kwargs):
        kwargs = kwargs or {}
        new = self.__class__( self.proc)
        new.function  = self.functions.copy(True) # make a deep copy

        new.update(*args, **kwargs)
        return new

    def get(self, key, default=False):
        return self.functions[key].get(default)

    def set(self, key , val):
        self.functions[key] = val

    def update( self, *args, **kwargs):
        return self.functions.update( *args, **kwargs)

    def cmd(self, *args, **kwargs):
        self = self.copy()
        vals = self.functions#.copy()
        vals.update(*args, **kwargs)
        vals = vals.rcopy()
        #for k in self.mandatory:
        #    if not vals[k].hasValue():
        #        self.set( k, vals[k].get(True)) # copy is default to value for mandatory

        cmds = vals.cmd(context = self)
        return cmd(cmds)

    def sequence(self, method, *args, **kwargs):
        if issubclass(type(method), str):
            method = self.__getattribute__(method)
        elif not hasattr(self, "__call__"):
            raise TypeError("Method shoud have a __call__ method")
        return Sequence( ( method, args, kwargs) )

    def setup(self, kwargs=None , expoId=0, timeout=None):
        kwargs = kwargs or {}
        return self.proc.msgSend("setup", dict(function=self.cmd(kwargs), expoId=expoId), timeout= timeout)


class MethodArgsList(list):
    def call(self):
        out = []
        for method,args,kwargs in self:
            if len(kwargs) and "kwargs" in method.im_func.func_code.co_varnames:
                tmp = method(*args, kwargs=kwargs)
            else:
                tmp = method(*args, **kwargs)
            out.append(tmp)
        return out
    def control(self):
        for method,args,kwargs in self:
            print method,args,kwargs


_loop_class = (list, tuple)
class Sequence(object):
    def __init__(self, *m_args, **options):

        self.m_args = self._check_m_args(m_args)
        self.counter = -1
        size = options.pop("size", None)
        modulo = options.pop("modulo",False)
        if len(options):
            raise KeyError("Accept only size and modulo keywords")
        if modulo:
            self.size = self.getMaxLen() if size is None else size
        else:
            self.size = self.checkLens(size)

    def getMaxLen(self):
        n = 0
        for m,args,kwargs in self.m_args:
            for k,p in kwargs.iteritems():
                if issubclass(type(p), _loop_class):
                    n = max(n,len(p))
            for p in args:
                if issubclass(type(p), _loop_class):
                    n = max(n,len(p))
                print p, n
        return n
    def checkLens(self, size):

        for m,args,kwargs in self.m_args:
            for k,p in kwargs.iteritems():
                if issubclass(type(p), _loop_class):
                    if size is None:
                        size = len(p)
                    elif len(p)!=size:
                        raise ValueError("list for keyword %s does not have the right len expected %d got %d"%(k,size,len(p)))

            for p in args:
                if issubclass(type(p), _loop_class):
                    if size is None:
                        size = len(p)
                    elif len(p)!=size:
                        raise ValueError("list for args num %d does not have the right len expected %d got %d"%(args.index(p),size,len(p)))

        return size


    def call(self):
        return self.rebuildMethodKwargs()

    @staticmethod
    def _check_m_args(m_args):
        out = []
        for m_a in m_args:
            if not issubclass( type(m_a), tuple):
                raise ValueError("Arguments must be tuple of one two or three")
            Nm_a = len(m_a)
            if Nm_a<1:
                raise ValueError("Empty tuple")

            if not hasattr( m_a[0], "__call__"):
                raise ValueError("first element of tuple must have a call method (a function ro class)")
            if Nm_a<2:
                args, kwargs = [], {}
            elif Nm_a<3:
                args , kwargs = m_a[1], {}
                if issubclass( type(args), dict): # reverse args and kwargs
                    args, kwargs = [], args

            elif Nm_a<4:
                args , kwargs = m_a[1:3]
            else:
                raise ValueError("tuple must have one two or three elements")
            if issubclass( type(args), dict): # reverse args and kwargs
                args, kwargs = kwargs, args
            if issubclass( type(args), dict) or issubclass( type(kwargs), (list,tuple)):
                raise ValueError("tuple must contain at least a method then a list or a dict or both")
            out.append( (m_a[0], args, kwargs.copy()))
        return out

    def rebuildMethodKwargs(self):
        out = []
        for m,a,kw in self.m_args:
            out.append( (m, self.rebuildArgs(a), self.rebuildKwargs(kw) ) )
        return MethodArgsList(out)

    def rebuildKwargs(self, kwargs):
        kout = kwargs.copy()
        for k,v in kwargs.iteritems():
            if issubclass( type(v), _loop_class):
                kout[k] = v[self.counter%len(v)]
        return kout

    def rebuildArgs(self, args):
        aout = []
        for a in args:
            if issubclass( type(a), _loop_class):
                aout.append(a[self.counter%len(a)])
            else:
                aout.append(a)
        return aout

    def next(self):
        if self.counter>=(self.size-1):
            raise StopIteration()
        self.counter += 1
        return self.call()

    def __iter__(self):
        self.counter = -1
        return self

    def go(self):
        return [ l.call() for l in self]

    def control(self):
        for l in self:
            l.control()


class Device(object):
    functions = FunctionDict()
    aliases = {}
    need    = []
    def __init__(self, proc=None, functions=None, aliases=None,
                 name=None, statusKeys=None, timeout=None):
        self.name = name
        self._proc = proc
        self.functions = self.functions.copy()

        if functions:
            self.init_functions(functions)
            #self.functions.update(functions)

        aliases = self.aliases.copy()
        if aliases: aliases.update(aliases)

        if aliases and len(aliases):
            self.functions = self.functions.copyWithAliases(aliases)

        #if self.need:
        #    for n in self.need:
        #        if not n in self.functions:
        #            raise KeyError("The device %s need the Function %s to work correctly"%(self.__class__,n))

        self.statusKeys = statusKeys
        self.timeout = timeout


        self.onStatus = Actions()
        self.onUpdate = Actions()
        self.onSetup  = Actions()

    def _get_function(self, key, functions):
        if key in functions:
            return functions[key]
        if key in self.functions:
           return self.functions[key]

    def init_functions(self, functions):
        pass


    def __getitem__(self, item):
        return self.functions[item]

    def __setitem__(self, item, val):
        self.functions[item] = val


    @classmethod
    def new(cls, proc, prefix, dictionary):
        return cls( proc, dictionary.restrict(prefix))

    def getProc(self, proc=None):
        return proc if proc is not None else getProc(self._proc)

    def setProc(self, proc):
        if not isinstance(proc, Process):
            raise ValueError("Expecting a Process got %s "%proc)
        self._proc = proc

    proc = property(fget=getProc, fset=setProc)

    def getTimeout(self, timeout=None):
        return timeout if timeout is not None else self.timeout

    def setTimeout(self, timeout):
        self.timeout = int(timeout)

    def status(self, keys=None, proc=None):
        out = self.functions.status(
            keylist=(keys if keys is not None else self.statusKeys),
            proc = self.getProc(proc)
        )
        self.onStatus.run(self,out)
        return out

    def update(self, keys=None, proc=None):
        self.functions.statusUpdate(keylist=(keys if keys is not None else self.statusKeys),
                                    proc=self.getProc(proc)
                                )
        self.onUpdate.run(self)

    def setup(self, values=None, proc=None, default=False, **kwargs):
        out = self.functions.setup(values=values, context=self,
                                   proc=self.getProc(), default=default,
                                   **kwargs)

        self.onSetup.run(self)
        return out

    def cmd(self, values=None, default=False):
        return self.functions.cmd( values=values, default=default)

    def keywords( self, kw):
        return deviceKeywords("INS.%s"%(self.name), kw)

    def sequence(self, method, *args, **kwargs):
        if issubclass(type(method), str):
            method = self.__getattribute__(method)
        elif not hasattr(self, "__call__"):
            raise TypeError("Method shoud have a __call__ method")
        return Sequence( ( method, args, kwargs) )






def newDevice( name, proc, dictionary,   cls=Device):
    new = cls(name, proc)
    res = proc.status(function=name)

    new.functions = FunctionDict()
    namelen = len(name)
    for k,v in res.iteritems():
        nk = k[namelen+1:None]
        new.functions[nk] = dictionary[k]

    return new

class DeviceKeywords(dict):
    name = ""
    def __getitem__(self, item):
        tmpi = "%s.%s"%(self.name, item.upper())
        item = tmpi if tmpi in self else item
        return super(DeviceKeywords, self).__getitem__(item)

def deviceKeywords( name, kw):
    kw = DeviceKeywords(kw)
    kw.name = name
    return kw



class Instrument(Process):

    def __init__(self, init=True):
        self._init_dictionaries

    def _init_dictionaries(self):
        pass








def _updatedm(dm):
    dm.updateZernStatus()
    dm.updateActStatus()

class DM(Device):
    functions = None
    allfunctions = None
    xtilt = "ZERN3"
    ytilt = "ZERN2"
    setup_callback = None


    def __init__(self,proc, pref, functions):
        self.proc = proc
        self.functions = functions.restrict(pref)
        self.allfunctions = functions
        self.prefix = self.functions._prefix


        self.onSetup  = Actions(_updatedm)
        self.onUpdate = Actions()
        self.onUpdateZern = Actions()
        self.onUpdateAct  = Actions()

    def __getitem__(self, item):
        return self.functions[item]

    def update(self, *args, **kwargs):
        return self.functions.update(*args, **kwargs)

    def set(self, k,v):
        return self.functions.set(k,v)

    def cmdSetup(self, dictval=None, **kwargs):
        cmd = []
        if dictval:
            kwargs.update(dictval)

        for k,v in kwargs.iteritems():
            self.set(k,v)
            cmd += self.functions[k].getCmd()
        return cmd

    def cmdTmpSetup(self, dictval=None, **kwargs):
        cmd = []
        if dictval:
            kwargs.update(dictval)

        for k,v in kwargs.iteritems():
            cmd += self.functions[k].getCmd(v)
        return cmd


    def setup(self, dictval=None, **kwargs):
        out = self.proc.setup(self.cmdSetup(dictval,**kwargs))
        self.onSetup.run(self)
        return out

    def tmpSetup(self, dictval=None, **kwargs):
        out = self.proc.setup(self.cmdTmpSetup(dictval,**kwargs))
        self.onSetup.run(self)
        return out

    def cmdTiptilt(self, x, y):
        return self.cmdSetup( {self.xtilt:x, self.ytilt:y} )


    def getTiptilt(self):
        return (self.functions[self.xtilt].get(), self.functions[self.ytilt].get())
    def parseTiptilt(self, x, y):
         return  {self.xtilt:x , self.ytilt:y}
    def tiptilt(self,x,y):
        return self.setup(self.parseTiptilt(x,y))

    def setOffset(self):
        return self.tmpSetup( {"OFVO.CTRL":"SET"})

    def resetOffset(self):
        return self.tmpSetup( {"OFVO.CTRL":"SET"})

    def saveOffset(self, fileName=None):
        cmd =  {"OFVO.FILE":fileName} if fileName else {}
        cmd["OFVO.CTRL"] = "SAVE"
        return self.tmpSetup(cmd)

    def loadOffset(self, fileName=None):
        cmd =  {"OFVO.FILE":fileName} if fileName else {}
        cmd["OFVO.CTRL"] = "LOAD"
        return self.tmpSetup(cmd)

    def load(self, fileName, mode="modal"):
        if not mode in ["modal", "local"]:
            raise KeyError("mode should be 'modal' or 'local'")
        if mode=="local":
            return self.tmpSetup( {"ACT FILE":fileName} )
        else:
            return self.tmpSetup( {"ZERN FILE":fileName} )

    def save(self, fileName, mode="modal"):
        try:
            import pyfits as pf
        except:
            from astropy.io import fits as pf
        import numpy as np

        if not mode in ["modal", "local"]:
            raise KeyError("mode should be 'modal' or 'local'")
        if mode == "local":
            N = self.getNact()
            data = [self.functions["ACT%d"%i].get() for i in range(1, N+1)]
        elif mode == "modal":
            N = self.getNzern()
            data = [self.functions["ZERN%d"%i].get() for i in range(1, N+1)]
            f = pf.PrimaryHDU(np.array( data, dtype=np.float64))

        return f.writeto(fileName, clobber=True)



    def cmdZern(self, modes):
        return self.cmdSetup(self.parseZern(modes))



    def getZern(self, z):
        return self.functions[self.parseZernKey(z)]

    def getZerns(self, lst=None, update=False):
        if lst is None:
            lst = range(1,self.getNzern()+1)
        funcs = self.functions.restrict( self.parseZernKeys(lst))
        if update:
            funcs.statusUpdate(None)
        return funcs

    def parseZernKey(self, m):
        if isinstance(m,str):
            if m[0:4].upper() == "ZERN":
                m = int(m[4:None])
            elif m[0:1].upper() == "Z":
                m = int(m[1:None])
            else:
                raise KeyError("cannot understand zernic key '%s'"%m)
        return "ZERN%d"%m

    def parseZernKeys(self, keys):
        return  [self.parseZernKey(m) for m in keys]

    def parseZern(self, modes):
        it = modes.iteritems() if isinstance(modes,dict) else enumerate(modes,1)
        setout = {}
        for m,v in it:
            if isinstance(m,str):
                if m[0:4].upper() == "ZERN":
                     m = int(m[4:None])
                elif m[0:1].upper() == "Z":
                     m = int(m[1:None])
                else:
                     raise KeyError("cannot understand zernic key '%s'"%m)
            setout["ZERN%d"%m] = v
        return setout

    def zern(self, modes, mode=None):
        dzern  = self.parseZern(modes)
        if mode:
            dzern.setdefault("CTRL OP",mode)
        return self.setup(dzern)

    def getAct(self, a):
        return self.functions[self.parseActKey(a)]

    def getActs(self, lst=None, update=False):
        if lst is None:
            lst = range(1,self.getNact()+1)
        funcs = self.functions.restrict( self.parseActKeys(lst))
        if update:
            funcs.statusUpdate(None)
        return funcs

    def getZernValues(self, lst=None, update=False):
        return self.getZerns(lst, update).todict()
    def getActValues(self, lst=None, update=False):
        return self.getActs(lst, update).todict()


    def parseActKey(self, m):
        if isinstance(m,str):
            if m[0:3].upper() == "ACT":
                m = int(m[3:None])
            elif m[0:1].upper() == "A":
                m = int(m[1:None])
            else:
                raise KeyError("cannot understand actuator key '%s'"%m)
        return "ACT%d"%m

    def parseActKeys(self, acts):
        return [self.parseActKey(m) for m in acts]


    def parseAct(self, acts):

        it = acts.iteritems() if isinstance(acts,dict) else enumerate(acts,1)
        setout = {}
        for m,v in it:
            if isinstance(m,str):
                if m[0:3].upper() == "ACT":
                     m = int(m[3:None])
                elif m[0:1].upper() == "A":
                     m = int(m[1:None])
                else:
                     raise KeyError("cannot understand actuator key '%s'"%m)
            setout["ACT%d"%m] = v
        return setout
    def cmdAct(self, acts):
        return self.cmdSetup(self.parseAct(acts))

    def act(self, acts, mode=None):
        dact  = self.parseAct(acts)
        if mode:
            dact.setdefault("CTRL OP",mode)
        return self.setup(dact)

    def cmdReset(self):
        return self.cmdSetup(self.getReset())
    def getReset(self):
        return {"CTRL.OP":"RESET"}

    def reset(self):
        return self.setup(self.getReset())

    def getNact(self):
        return self.allfunctions["AOS.ACTS"].getOrUpdate(proc=self.proc)
    def getNzern(self):
        return self.allfunctions["AOS.ZERNS"].getOrUpdate(proc=self.proc)

    def status(self, keylist=None):
        return self.functions.status(keylist, proc=self.proc)

    def statusUpdate(self, keylist=None):
        return self.functions.statusUpdate(keylist, proc=self.proc)


    def getActStatus(self, nums=None, indict=None):
        return self.getIterableKeysStatus("ACT", nums or self.getNact(), indict=indict)

    def updateActStatus(self, nums=None, indict=None):
        out =  self.updateIterableKeysStatus("ACT", nums or self.getNact(), indict=indict)
        self.onUpdateAct.run(self)
        return out

    def updateZernStatus(self, nums=None, indict=None):
        out =  self.updateIterableKeysStatus("ZERN", nums or self.getNzern(), indict=indict)
        self.onUpdateZern.run(self)
        return out

    def getZernStatus(self, nums=None, indict=None):
        return self.getIterableKeysStatus("ZERN", nums or self.getNzern(), indict=indict)

    def updateAll(self):
        keys = ["%s%d"%("ZERN",i) for i in range(1,self.getNzern()+1)]+["%s%d"%("ACT",i) for i in range(1,self.getNact()+1)]
        self.functions.restrict(keys).statusUpdate(None)
        self.onUpdate.run(self)

    def updateIterableKeysStatus(self,key , nums, indict=None):
        if isinstance(nums, int):
            nums = range(1,nums+1)
            if indict is None:
                indict = True
        else:
            indict = False

        keys  = ["%s%d"%(key,i) for i in nums]
        frest = self.functions.restrict(keys)
        frest.statusUpdate(None)

        self.onUpdate.run(self)

        if indict:
            return {n:frest["%s%d"%(key,n)].get() for n in nums}
        else:
            return [frest["%s%d"%(key,n)].get() for n in nums]

    def getIterableKeysStatus(self,key , nums , indict=None):
        if isinstance(nums, int):
            nums = range(1,nums+1)
            if indict is None:
                indict = False
        else:
            indict = True

        keys = ["%s%d"%(key,i) for i in nums]
        vals = self.status(keys)

        pref = self.functions._prefix+"." if self.functions._prefix else ""
        if indict:
            return {n:vals[pref+"%s%d"%(key,n)] for n in nums}
        else:
            return [vals[pref+"%s%d"%(key,n)] for n in nums]





class DMs(list):
    def plot(self, axes=None, fig=None, vmin=None, vmax=None, cmap=None):
        if axes is None:
            if fig is not None:
                axes = fig.get_axes()
            else:
                if self[0].graph:
                    import math as m
                    N = len(self)
                    nx = int(m.sqrt(N))
                    ny = int(m.ceil(N/float(nx)))
                    fig = self[0].graph.plt.figure("actuactors")
                    fig.clear()
                    axes = [fig.add_subplot(nx,ny, i+1) for i in range(N)]
                    #fig, axes = self[0].graph.plt.subplots(nx,ny)
                    #axes = axes.flatten().tolist()
        if len(axes)<len(self):
            raise Exception("not enought axes to plot %d dm"%(len(self)))

        for i in range(len(self)):
            a  = axes[i]
            dm = self[i]
            dm.plot(axes=a, vmin=vmin, vmax=vmax, cmap=cmap )

    def plotzern(self, axes=None, fig=None, **kwargs):
        if axes is None:
            if fig is not None:
                axes = fig.get_axes()
            else:
                if self[0].zerngraph:
                    import math as m
                    N = len(self)
                    nx = int(m.sqrt(N))
                    ny = int(m.ceil(N/float(nx)))
                    fig = self[0].graph.plt.figure("zernics")
                    fig.clear()
                    axes = [fig.add_subplot(nx,ny, i+1) for i in range(N)]
                    #fig, axes = self[0].graph.plt.subplots(nx,ny)
                    #fig, axes = self[0].graph.plt.subplots(N)
                    #axes = axes.flatten().tolist()
                else:
                    raise Exception("no zeengraph set")
        if len(axes)<len(self):
            raise Exception("not enought axes to plot %d dm"%(len(self)))
        print kwargs
        for i in range(len(self)):
            a  = axes[i]
            dm = self[i]
            dm.plotzern(axes=a, **kwargs)



    def reset(self):
        for dm in self:
            dm.reset()

    def zern(self, modes):
        for dm in self:
            dm.zern(modes)
    def act(self, actvals):
        for dm in self:
            dm.act(actvals)



