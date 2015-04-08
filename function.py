
import re
from .action import Actions
from .mainvlt import cmd, getProc, dotkey, undotkey
from .config import config
KEY_MATCH_CASE = config.get("key_match_case", False)

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
    _value    = None
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
        self.setDescription(description)
        self.setUnit(unit)
        self.setContext(context)
        self.setCls(cls)



    def _new(self, **attr):
        return self._copyAttr(self.__class__("",_void_=True), **attr)
    def _copyAttr(self, new, **attr):
        for k in ["params", "msg","_value", "index", "onValueChange",
                  "onSetup","onSelect", "onUnSelect",
                  "selected", "statusFunc"]:
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


    def __setitem__(self, item, value):
        self[item].set(value)

    def __iter__(self):
        if not self.isIterable():
            raise Exception("function '%s' is not iterable"%(self.getMsg()))
        return self._value.__iter__()

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

            if self._value is None:
                self._value = {}

            if i.isIterable():
                ####
                # Just copy the actual iterable function but with a the new indexed msg
                ####
                return self._new(msg=newmsg )
            else:
                ####
                # freeze the curent key, it becomes not-iterable/no-index  anymore
                ####
                i  = FunctionKey(i.reform(), None)
                newmsg.keys[j] = i
                if not "%s"%i in self._value:
                    keypref = newmsg.keys[0:j+1]
                    ####
                    # To create a new iterabke function we need to be sure that all the keys
                    # above are in the raw form "KEYi"
                    ####
                    keyrest = [FunctionKeyi(s.key, None) if s.hasIndex() else s for s in newmsg.keys[j+1:None]]
                    tmpmsg = FunctionMsg.new( keypref+keyrest, newmsg.sep)


                    self._value["%s"%i] = self._new(msg=tmpmsg ,
                                                    _value=None ,
                                                    onValueChange = self.onValueChange.derive(),
                                                    onSetup = self.onSetup.derive()
                    )
                self = self._value["%s"%i]
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
            keys = self._value.keys() if ikey else s.reformAll()

            if ikey and errorIfNoLen and (not len(keys)):
                raise Exception("Cannot iter on '%s', it has no len"%s)

            for k in keys:
                sub = self[k]
                funcs.extend(sub.functions(onlyIfHasValue=onlyIfHasValue, default=default))
            break
        return funcs

        self._function(self, funcs, 0)
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
                return {k:f.getValue(default=default, context=context) for k,f in self._value.iteritems() if f.hasValue()}

        if value is None:
            if self._value is None:
                return self.getDefault(context=context)
            value = self._value

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

            return sum( f.hasValue() for f in self._value.values() )>0

        return self._value is not None or (default and self.hasDefault())

    def isDeletable(self, index=None):
        self = self._getOrCreate(index)
        if self.isIterable():
             return sum( f.isDeletable() for f in self._value.values() )==0
        return not self.hasValue()

    def cleanUp(self, index=None):
        self = self._getOrCreate(index)
        if not self.isIterable():
            return
        for k,f in self._value.iteritems():
            f.cleanUp()
        for k in self._value.keys():
            if self._value[k].isDeletable():
                del self._value[k]

    def select(self, id=True):
        self.selected = id
        self.onSelect.run(self)
    def unselect(self):
        self.selected = False
        self.onUnSelect.run(self)

    def isSelected(self, id=True):
        """ Return true is the function is selected.
        id is the id selection test.
        """
        if id is True:
             return self.selected is not False
        return self.selected == id

    def selectUnselect(self, id=True):
        if self.isSelected(id):
             self.unselect()
        else:
             self.select(id)


    def hasDefault(self):
        """ return True if function has a default values"""
        return self.default is not None


    def setValue(self, value, index=None):
        """ set the function value.
        the value must be parsed by dtype
        """
        self = self._getOrCreate(index)

        if self.isIterable():
            if value is None:
                self._value = {}
                return


            if not isinstance( value, dict):
                map( lambda f:f.setValue(value), self.functions(onlyIfHasValue=False, errorIfNoLen=True) )
                return

            for k,v in value.iteritems():
                #self._getOrCreate((k,))[self.index].setValue(v)
                self[k].setValue(v)
                #self._getOrCreate((k,)).setValue(v)
            return
        oldvalue = self._value
        self._value = self.parseValue(value)
        self.onValueChange.run(self, oldvalue)

    set  = setValue

    def setComment(self,comment):
        self.params['comment'] = str(comment)
    def getComment(self):
        return self.params.get('comment', "")
    def setDescription(self, description):
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


    def match(self, key, context=None, prefixOnly=False, partialy=True):
        return self.getFunctionMsg().match(key,
                                           prefixOnly=prefixOnly,
                                           partialy=partialy
                                           )

    def isIterable(self):
        return self.getFunctionMsg().isIterable()


    def setDefault(self, default):
        if default is None and "default" in self.params:
            del self.params['default']
            return None
        self.params['default'] = self.parseValue(default)


    def getDefault(self, default=None , context=None):
        if not "default" in self.params or self.params['default'] is None:
            if default is not None:
                return default
            else:
                raise ValueError("'%s' has no default value"%(self.getMsg()))

        if context is not None:
            return self._rebuildVal(self.params["default"], context)
        return self.params["default"]


    def setFormat(self, fmt):
        if not issubclass( type(fmt), str) and not hasattr( fmt, "__call__"):
            raise ValueError("if format is not a string or tuple, should be a callable function or object ")
        self.params["format"] = fmt


    def getFormat(self, tp=0):
        if tp>1 or tp<0:
            raise ValueError("type must be 0 for setup format or 1 for rebuilt format")
        fmt = self.params.get("format", "%s")
        if issubclass( type(fmt), tuple):
            return fmt[type]
        return fmt


    def getDtype(self):
        return self.params.get("dtype", str)

    def setDtype(self, dtype):
        if dtype is bool:
            dtype = vltbool
        self.params["dtype"] = dtype

    def _cmdIterableWalker(self, dval, out , itr=[], context=None):
        if not isinstance( dval, dict):
            out += [(self.rebuildListMsg( tuple(itr)), self.formatValue(dval , context=context))]
            return None
        for k,v in dval.iteritems():
            self._cmdIterableWalker(v, out, itr+[k], context)

    @classmethod
    def _getAllIndexes(self, indexes):
        return self._getAllIndexesWalker( self._value, list(indexes))
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
             indexes = self._value.keys()

        if isinstance(indexes, slice):
             indexes = range( indexes.start or min(self._value.keys()),
                              indexes.stop  or max(self._value.keys())+1,
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

    def getFormatedValue(self, value=None, default=False, context=None, index=None):
        self = self._getOrCreate(index)

        if self.isIterable():
            return {k:f.getFormatedValue(value=value, default=default, context=context) for k,f in self._value.iteritems() if f.hasValue()}
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
        if hasattr(value, "__iter__"):
            if not self.isIterable():
                raise ValueError("got a iterable object but the option is not iterable")
            if isinstance(value, dict):
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

    def getProc(self, proc=None):
        return getProc(proc)
    proc = property(fget=getProc, doc="Function default process")

    def setup(self, value=None, proc=None, **kwargs):
        proc = getProc(proc)
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

    value    = property(fget=getValue, fset=setValue,
                        doc="function value")

    strvalue = property(fget=getFormatedValue, fset=setValue,
                        doc="function string value"
                        )
    format = property(fget=getFormat, fset=setFormat,
                      doc="Function format")
    dtype = property(fget=getDtype, fset=setDtype,
                      doc="Function data type")
    comment = property(fget=getComment, fset=setComment,
                       doc="Function comment field")
    unit  = property(fget=getUnit, fset=setUnit,
                       doc="Function Unit")
    description = property(fget=getDescription, fset=setDescription,
                           doc="Function description"
                           )
    context = property(fget=getContext, fset=setContext,
                       doc="Function context"
                       )
    cls = property(fget=getCls, fset=setCls,
                   doc="Function Class list"
                   )



