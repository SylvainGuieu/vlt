import re
from .mainvlt import dotkey, undotkey, EmbigousKey
from .function import Function, upperKey, FunctionMsg
from .process import getProc
from .action import Actions
from .config import config
from .process import Process
KEY_MATCH_CASE = config.get("key_match_case", False)



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
    """ return a FunctionDict from a list of Function or string
    or tuple defining the function.
    """
    fd = FunctionDict()
    fd.add(*args)
    return fd

def _test_rec_value(ftest, f, out):
    if not f.isIterable():
        if ftest(f.getValue()):
            out[f.getMsg()] = f
        return

    for k in f:
        _test_rec_value(ftest, f[k], out)



class FunctionDict(dict):
    keySensitive  = False
    dotSensitive  = False
    noDuplicate   = False

    _child_object = Function
    _prefix = None
    _proc = None
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
            return proc if proc is not None else getProc(self._proc)
        except:
            raise Exception("No default process in the FunctionDict neither in the VLT module")

    def setProc(self, proc):
        if not isinstance(proc, Process):
            raise ValueError("Expecting a procees object")
        self._proc = proc
    proc = property(fget=getProc, fset=setProc,
                    doc="vlt process run .proc.help() for more doc"
                    )

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
                t = test( p,getmethod(f))
                if isinstance(t, tuple): # got a test, key pair
                    t, matched_f = t
                    out[matched_f.getMsg()] = matched_f
                elif t:
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
        """ return a restricted FunctionDict of Function with the given value

        if value is a list, return Function of all matched values.
        value can be a function that takes one argument (the value to test)

        The test is executed only on Functions that has a value, so :
              d.restrictValue( lambda v:True)
            is equivalent to
              d.restrictHasValue()

        Examples:
            d.restrictValue([1,10])
            d.restrictValue(lambda v:v>1.0)
            d.restrictValue(lambda v: v is "TEMPERATURE")

        """

        if hasattr(value, "__call__"):
            ftest = value
        else:
            if not isinstance(value , (list,tuple)):
                value = [value]
            ftest = lambda v: v in value

        out = {}
        for k,f in self.restrictHasValue().iteritems():
             _test_rec_value(ftest, f, out)

        return self._copy_attr( self.__class__(out))

        return self.restrictHasValue().restrictParam([value],
                                                     lambda f: f,
                                                     _test_rec_value)

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
        return self.restrict([k for k,f in self.iteritems() if f.match(pattern)])


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
        new._proc    = self._proc
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


    def tocmd( self, values=None, withvalue=True, include=None,
              default=False,
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
                        funcs.append(f)
        if include:
            for k in include:
                f = self[k]
                if not f in funcs:
                    if not f.hasValue():
                        raise ValueError("Key '%s' is mandatory but do not have value set" % f.getMsg())
                    out.extend(f.cmd(default=default, context=context))

        return out
    cmd = tocmd

    def qcmd(self, _values_=None, _include_=None, **kwargs):
        values = _values_ or {}
        values.update(kwargs)
        return self.cmd(values, False, include=_include_)

    def setup(self, values=None, include=None,
              withvalue=True, default=False, context=None,
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
                             include=include,
                             default=default, context=context,
                             contextdefault=contextdefault)

        cmdfunc = cmdfunc+kwargs.pop("function",[])

        out = self.getProc(proc).setup(function=cmdfunc, **kwargs)

        self.onSetup.run(self)
        return out

    def qsetup(self, _values_=None, _include_=None, **kwargs):
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

        cmdfunc = self.qcmd(_values_, _include_=_include_, **kwargs)+pkwargs.pop("function",[])

        out = self.getProc(proc).setup(function=cmdfunc, **pkwargs)

        self.onSetup.run(self)
        return out

