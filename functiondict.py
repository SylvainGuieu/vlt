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
    """ Collection of Function with handy methods.

    



    """
    keySensitive  = False
    dotSensitive  = False
    noDuplicate   = False

    _child_object = Function
    _prefix = None
    _proc = None
    _context = None

    statusItems = None

    onSetup  = None # ignitialised in __init__
    onUpdate = None
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
            see method .setVal for more help
        """
        # setitem understand what to do function to the value
        # if value is a self._child_object it will be set like on a dictionary
        # else try to set the value inside the _child_object, if that case if the key does not
        # exists raise a KeyError

        if issubclass(type(item), tuple):
            if len(item)>2:
                raise IndexError("axcept no more than 2 items, second item should be a string")

            if len(item)>1:
                self[item[0]][item[1]] = val
                return None
            else:
                # case of  f[key,] by default this is "value"
                self[item[0]]["value"] = val
                return None

        return self.setVal(item, val)


    def __contains__(self,item):
        if super(FunctionDict, self).__contains__(item):
            return True

        context = self.getContext()
            
        keys = FunctionMsg(dotkey(item))
        for f in self.itervalues():
            if f.match(keys, context=context):
                return True
        if False and self._prefix:
            item = "%s.%s"%(self._prefix,keys)
            for f in self.itervalues():
                if f.match(keys, context=context):
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

    def restrict(self, preforlist, context=None):
        """ restrict the FunctionDict to matched items

        Parameters
        ----------
        preforlist : string or list of string

            - if a string. in this case the returned dictionary will be restricted
            to all Function with a key starting by the string
            e.g.:

                d = vlt.functionlist( "INS1.OPT1.NAME grism", "INS1.OPT1.ENC 1200",
                                      "INS1.OPT2.NAME grism", "INS1.OPT2.ENC 800")

                restricted = d.restrict("INS1.OPT1")

            return a dictionary with only the element starting by "INS1.OPT1"
            The "INS1.OPT1" will be dropped in the return dictionary.
            So restricted["NAME"] will work but conveniently
            restricted["INS1.OPT1.NAME"] will work as well

            - if a list of string keys:
                the returned FunctionDict will be restricted to the matched keys

        context : any object, optional 
            the context object use to rebuild Function keys if needed. 
            see setContext method help for more info. 

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary                

        See Also
        ---------
        restrictClass, restrictContext, restrictValue, restrictHasValue,
        restrictHasNoValue

        Examples
        --------
        restricted = fd.restrict("INS.SENS1")

        """
        context = self.getContext(context)

        if issubclass( type(preforlist), str):
            pref = dotkey(preforlist)
            out = {}

            for k,f in self.iteritems():
                m = f.match(pref, context=context, prefixOnly=True)
                if m:
                    nf = f[m.indexes] if m.indexes else f
                    out[m.suffix] = nf

            if self._prefix: # try the same with prefix
                pref = dotkey("%s.%s"%(self._prefix,preforlist))
                m = f.match(pref, context=context, prefixOnly=True)
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

        Parameters
        ----------
        cls : string, list
            can be a string or a list of string match 

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary

        """
        return self.restrictParam(cls, self._child_object.getCls, lambda p,l:p in l)

    def restrictContext( self, context):
        """ return a restricted FunctionDict of Function of 'context' context

        Parameters
        -----------
        context : string, list
            can be a string or a list of string match 

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary    
        """
        return self.restrictParam(context, self._child_object.getContext, lambda p,l: p==l)

    def restrictValue(self, value):
        """ return a restricted FunctionDict of Function with the given value

        Parameters
        ----------
        value : any or method 

            If value is a list, return Function of all matched values.
            value can be a function that takes one argument (the value to test)

            The test is executed only on Functions that has a value, so :
                d.restrictValue( lambda v:True)
            is equivalent to
                d.restrictHasValue()

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary        

        Examples
        --------
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
        """ Return a FunctionDict restrited to functions with value defined

        Parameters
        -----------

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary 

        """
        return self.restrict([k for k,f in self.iteritems() if f.hasValue()])

    def restrictHasNoValue(self):
        """ Return a FunctionDict restrited to functions *without* value defined

        Parameters
        -----------

        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary 
        """
        return self.restrict([k for k,f in self.iteritems() if not f.hasValue()])

    def restrictMatch(self, pattern, context=None):
        """ Reutnr a FunctionDict restricted to mathed Key Function

        Parameters
        ----------
        patern : string
            the patern to be matched in the function names
         e.g.:  restrictedMatch( "VALUE")
          will return a FunctionDict containing the "VALUE" key like
             for instance  "INS1.FILT1.VALUE"

        context : any object, optional 
            the context object use to rebuild Function keys if needed. 
            see setContext method help for more info. 
                        
        Returns
        -------
        df : FunctionDict
            Restricted FunctionDictionary      
             
        """
        context = self.getContext(context)
        return self.restrict([k for k,f in self.iteritems() if f.match(pattern, context=context)])


    def has_key(self,key):

        return key in self


    def add(self, *args):
        """ Add item(s) to the dictionary. 

        Parameters
        ----------
        *items : Function or string or tuple 
            - if Function. Added as it is 
            - if string. Should be a space separated key value string which will be converted 
                on the fly to a new function.
            - if tuple. should be a 2 tuple (key, value) pair which will be converted 
                on the fly to a new function.
                       
        Returns
        -------
        None

        Examples
        --------

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

    def setVal(self, item, val):
        """ Set a function child  value 

        fd.setVal(item, value) equivalent to fd[item] = value 

        Parameters
        ----------
        item : string
            The function item to be modified.
            

        value : Function or tuple or any value 
            If the item *already exists* in the FunctionDict the value can be both:
                - a new Function object (will replace the previous) 
                - a value (str, int, etc ...) in that case the value is set in 
                  the coresponding Function.
            If the item *does not exists* value should be: 
                - a Function object 
                - a (key, value) pair : key being the function message (e.g. 'ISN1.OPT1.VALUE')     
                


        Examples
        ---------
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
        """ Look if can find a iterable param  that match a numbered param

        e.g.  "DET0 SUBWIN4" should return True if "DETi SUBWINi" exists
        """
        return self.getIterableKeyLike(key)[0] in self

    def getContext(self, context=None):
        """ get the default FunctionDict context 

        context is any object that is used to rebuild Function keys or function
        values. If a key contains {var} var is searched in context['var'] and 
        {var} is replaced by its string value representation.

        Parameters
        ----------
        context : any object, optional 
            An alternative context, if not None, that him which
            will be returned 

        Returns:
        context : any object 
            the recorded or user provided context     
        """
        if context is None:
            context = self._context   

        if context is False:
            return None

        if context is True:    
            return self

        return context    

    def setContext(self, context):
        """ set the default FunctionDict context 

        Parameters
        ----------
        context : any object 
            the context object to be recorded as default
        Returns
        -------
        None    
        """
        self._context = context

    @property
    def context(self):
        """ FunctionDict context 

        if setted as True, the context is the FunctionDict itself
        """
        return self.getContext()

    @context.setter
    def context(self, context):
        self.setContext(context)


    def update(self, __d__={}, **kwargs):
        """ Upadte the FunctionDict with new values of Functions 

        All values should follow the setVal method protocol

        Parameters
        ----------
        fd : dict or FunctionDict or list of item/value pairs
            The item/function or item/tuple or item/value pairs 
            (see setVal)
        **kwargs : dict
            additional pairs, overwrite the one of *fd*    

        Returns
        -------
        None    

        """    
        iterator = __d__.iteritems() if isinstance( __d__, dict) else __d__

        for k,a in iterator:
            self[k] = a

        for k,a in kwargs.iteritems():
            self[k] = a

    def set(self, *args, **kwargs):
        """ alias of update except that set return the object for quick access 

        Parameters
        ----------
        see update

        Returns
        -------
        fd : FunctionDict
            the called FunctionDict : e.i.  fd.set() is fd  -> True 

        Example
        -------
            df.set(dit=0.003).setup()
            
        """
        self.update(*args, **kwargs)
        return self

    def get(self, item, default=None, context=None):
        """ get a Function inside the FunctionDict 

        fd.get(item) is equivalent to fd[item]

        Parameters
        ----------
        item : string
            the item string to match either the FunctionDict key or a 
            child Function key.
            meaning that :
                fd = vlt.FunctionDict(  dit=vlt.Function("DET1.DIT", 0.003) )
                fd.get("dit")
                fd.get("DET1.DIT")
                fd.get("DIT") 
            are equivalent because is not embigous.
            However in embigous case : 
                fd = vlt.FunctionDict(  dit =vlt.Function("DET1.DIT", 0.003),
                                        ndit=vlt.Function("DET1.NDIT", 10)
                                    )
                fd.get("dit") -> ok
                fd.get("ndit") -> ok 
                fd.get("NDIT") -> ok 
                fd.get("DET1.NDIT") -> ok 
                fd.get("DET1") -> *NOT OK* raise a embigousKey error: 
                    EmbigousKey: "Embigous key 'DET1'"
                                        
        default : Function
            a default Function object if the item is not in the FunctionDict  

        Returns
        -------
            f : the found child Function   

        Raises
        ------
            EmbigousKey : if item key is embigous    

        """
        if default is not None and not isinstance(default, self._child_object):
            raise ValueError( "default should be None or a %s object "%self._child_object)

        context = self.getContext(context)    

        if super(FunctionDict, self).__contains__(item):
            return super(FunctionDict, self).get(item, default)
        if not KEY_MATCH_CASE:
            uitem = upperKey(item)
            if super(FunctionDict, self).__contains__(uitem):
                return super(FunctionDict, self).get(uitem, default)

        fout = None
        for f in self.values():
            m = f.match(item, context=context)
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
                m = f.match(item, context=context)
                if m:
                    if fout:
                        raise EmbigousKey("Embigous key '%s'"%item)
                    fout = f[m.indexes] if m.indexes else f
                    if not m.partialy: break #no embiguity stop here
        if fout:return fout

        return default

    def _status(self, statusItems=None, proc=None):
        statusItems = statusItems or []
        return self.getProc(proc).status(function=statusItems)

    _spacereg = re.compile("[ ]+")
    def status(self, statusItems=None, proc=None, indict=False):
        """ status return a dictionary of key/value pairs returned from the process


        Parameters
        ----------
        statusItems : list or string or False or None, optional
            - if string must be space separated items ("DIT NDIT" equivalent to ["DIT", "NDIT"])
                is transformed to a list.
            - if None the default fd.statusItems is used
            - if explicitely False all the items of the dictionary are used to ask status

            The items in statusItems are used to query the process. Some time items cannot
            be parsed in the status command. For instance, to know the status of a device
            only the e.g. 'INS.OPTI3' key is needed to query all information about INS.OPTI3

        proc : Process, optional
            If None use the default process of this FunctionDict or the default process
            ( see vlt.setDefaultProcess ) raise an Exception if no process can be found.    


        indict : bool, optional 
            if True the key/pairs results are returned in a classic dictionary
            if False (default) resutls is returned in a FunctionDict      

        Returns
        -------
            fd : dict or FunctionDict
                the key/value pairs returned 

        Examples
        --------
            statusvalue = fd.status( ["INS.OPT3", "INS.SHUT1"] )

        See Also Method
        ---------------
            statusUpdate :  update the dictionary value returned by the process status command    
        """
        if statusItems is None:
            statusItems = self.statusItems

        if isinstance(statusItems, str):
            statusItems = self._spacereg.split(statusItems)
        
        if (statusItems is None) or (statusItems is False):
            # Take alle the keys to ask status 
            statusItems = self.keys()

        if statusItems:
            statusMsg = [self[k].getMsg() for k in statusItems]

        st = self.getProc(proc).status(function=statusMsg)
        valdict = st

        if indict:
            return valdict
        return self.dict2func(valdict)

    def dict2func(self, dictval):
        """ Transform a dictionary to a new  FunctionDict 

        If the item is present in the FunctionDict the matched Function is copied 
        and the value is update to the copy. If the item is not present a new Function
        is created as Function(key, value).

        This method allows to use a FunctionDict as a template.

        Parameters
        ----------
        dictval : dict like object
            key/value pairs to be transfomed to Function

        Returns
        -------
        fd : created FunctionDict obect

        """
        output = FunctionDict()
        for k,v in dict(dictval).iteritems():
            ks = self.key(k)
            if ks:
                f = self[ks].copy()
                f.set(v)
                output[ks] = f
            else:
                output[k] = Function(k,v)
        return self._copy_attr(output)

    def statusUpdate(self, statusItems=None, proc=None):
        """ Update the disctionary Function values from the Process.

        Parameters
        ----------
        statusItems : list or string or False or None, optional
            - if string must be space separated items ("DIT NDIT" equivalent to ["DIT", "NDIT"])
                is transformed to a list.
            - if None the default fd.statusItems is used
            - if explicitely False all the items of the dictionary are used to ask status

            The items in statusItems are used to query the process. Some time items cannot
            be parsed in the status command. For instance, to know the status of a device
            only the e.g. 'INS.OPTI3' key is needed to query all information about INS.OPTI3

        proc : Process, optional
            If None use the default process of this FunctionDict or the default process
            ( see vlt.setDefaultProcess ) raise an Exception if no process can be found.    


        Returns
        -------
            fd : FunctionDict
                A restricted vertion of the FunctionDict. Restricted to items that 
                has been updated. 

        Examples
        --------
            fd.statusUpdate( ["INS.OPT3", "INS.SHUT1"] )

        See Also Method
        ---------------
            status :  get the status key/pair values without affecting the FunctionDict        
        
        """
        vals = self.status(statusItems, proc=proc, indict=True)
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
        new.__dict__.update(self.__dict__)
        return new
        #new._proc    = self._proc
        #new.onSetup  = self.onSetup
        #new.onUpdate = self.onUpdate
        #new._prefix  = self._prefix
        #new._context = self._context        
        #return new

    def setAliases(self, __aliases__={}, **aliases):
        """ set Function aliases 

            fd.setAliases( dit="DET1.DIT", ndit="DET1.NDIT")    
        is equivalent to :
            fd["dit"]  = fd["DET1.DIT"]
            fd["ndit"] = fd["DET1.NDIT"]

        Parameters
        ----------
        aliases : dict like object, optional
        **aliases : additional alias/key pairs 

        Returns
        -------
        None


        """
        aliases = dict(__aliases__, **aliases)
        
        for k,alias in aliases.iteritems():
            self[alias] = self[k]


    def copy(self, deep=False, trueKey=False):
        """ Copy the FunctionDict 

        Parameters
        ----------
        deep : bool, optional
            if True the child Function are copied in the FunctionDict copy.
            if False (default) the child Function are not copied. 
            Meaning that:
                fd["DET.DTI"] is fd.copy()["DET.DIT"]
                fd["DET.DTI"] is not fd.copy(True)["DET.DIT"]

        trueKey : bool, optional
            If True the FunctionDict will have the true Function Keys as keys, 
                meaning that any aliases will be droped.
            If False (default) keys are copied as they are in the original FunctionDict
        
        Returns
        -------
        fd : FunctionDict
            The copied FunctionDict


        """
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
        """ Return a restricted copy of a FunctionDict with only the Function with value set

            df.rcopy() 
        is equivalent to 
            df.rcopy().restrictHasValue()

        Parameters
        ----------
        deep : bool, optional 
            default if False see method copy for more details
        default : bool, optional 
            if True copy also the Function that have default value     
            **The default capability may be dropped in future release** 

        Returns
        -------
        fd : FunctionDict
            The copied FunctionDict    
        
        """
        if deep:
            return self._copy_attr( self.__class__({k:f.copy() for k,f in self.iteritems() if f.hasValue(default=default)}))

        return self._copy_attr( self.__class__({k:f for k,f in self.iteritems() if f.hasValue(default=default)}))


    def msgs(self, context=None):
        """ Return the list of keys (or message) for all child Function
        
        Parameter:
        context : any object, optional 
            An alternative context, see getContext method 

        """
        context = self.getContext()
        return [f.getMsg(context=context) for f in self.values()]

    def todict(self, context=None, default=False):
        """ Create a symple dictionary of all key/value pairs that have a value set

        Parameters
        ----------
        context : any object, optional
            context object to rebuild key and values if needed 
            see method  getContext()
        default : bool, optional
            True/False use/no use default if value is not set
            **default** may be deprecated in future release

        Returns
        -------
        d : dict 
            A dictionary of key/value pair for all function with a value set
        """
        context = self.getContext()
        return {k:f.get(default=default, context=context) for k,f in self.iteritems() if f.hasValue(default=default)}

    def toalldict(self, default=False, context=None, exclude=[]):
        """ same than `todict` method except that aliases are added to the list of keys 


        Parameters
        ----------
        context : any object, optional
            context object to rebuild key and values if needed 
            see method  getContext()
        default : bool, optional
            True/False use/no use default if value is not set
            **default** may be deprecated in future release
        exclude : list of Function
            Functions instances to be exclude from result    

        Returns
        -------
        d : dict 
            A dictionary of key/value pair for all function with a value set
        """
        output = {}
        for k in set( self.keys()+self.msgs(context=context)):
            f = self[k].get(default=default)
            if not f in exclude:
                output[k] = f
        return output        
        #return {k:self[k].get(default=default) for k in set( self.keys()+self.msgs(context=context))}


    def tocmd( self, values=None,  include=None, withvalue=True,
              default=False,
              context=None, contextdefault=True):
        """ make a list of commands ready to be parsed to process
        
        cmd is an alias of tocmd 

        Parameters
        ----------
        values : dict, optional  
            A key/value pairs to be parsed temporary in the result, without changing
            values set inside the FunctionDict.

        include : list, optional
            A list of keys of Function to be include, make sense to use if withvalue
            is false e.g.  fd.tocmd(withvalue=False, include=["DET.DIT", "DET.NDIT"])    

        withvalue : bool, optional
            If True (default), add the command pair to all the child Function
            that has a value defined otherwise setup only the Function from the 
            input *values* dictionary.
            
        default : bool optional
            if True use default if value is not set
            **default can be deprecated in future release** 
       
        context : any object, optional 
            context is used as replacement for string value and or keys.
            Context can be any object with a obj[item] and/or obj.attr capability

            bracketed keys or values are replaced by its target value
            For instance:
                - "{[DPR.TYPE]}" will be replaced by the value context["DPR.TYPE"]
                - "INS OPT{.number}" will be "INS OPT"+context.number
            see getContext method     

        Returns
        -------
        List of (key,string value) pair ready to be passed in setup process

        Examples:
        --------

            fd = FunctionDict(type = Function("DPR.TYPE", value="test"),
                              file = Function("DPR.FILE", value="result_{[type]}_{[dit:2.3f]}.fits"),
                              dit = Function("DET.DIT", value=0.1)
                              )
            fd.tocmd(context=fd)
                [('DET.DIT', '0.1'), ('DPR.TYPE', 'test'), ('DPR.FILE', 'result_test_0.100.fits')]

        """
        if values:
            self = self.copy(True)
            for k,f in values:
                self[k] = f
        else:
            values = {}    
        

        context = self.getContext(context)
        
                
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
        """ Do the same thing than cmd but accept any keywords for key/value pairs 

        see cmd or tocmd method 
        """
        values = _values_ or {}
        values.update(kwargs)
        return self.cmd(values, include=_include_)

    def setup(self, values=None, include=None,
              withvalue=True, default=False, context=None,
            proc=None, contextdefault=True, function=[], **kwargs):
        """ Send a Setup from all the child Function with a value set.

        This call the tocmd method, so method parameter are the same some related
        to processes. 

        Parameters
        ----------
        values : dict, optional  
            A key/value pairs to be parsed temporary in the result, without changing
            values set inside the FunctionDict.

        include : list, optional
            A list of keys of Function to be include, make sense to use if withvalue
            is false e.g.  fd.tocmd(withvalue=False, include=["DET.DIT", "DET.NDIT"])    

        withvalue : bool, optional
            If True (default), add the command pair to all the child Function
            that has a value defined otherwise setup only the Function from the 
            input *values* dictionary.
            
        default : bool optional
            if True use default if value is not set
            **default can be deprecated in future release** 



        context : any object, optional 
            context is used as replacement for string value and or keys.
            Context can be any object with a obj[item] and/or obj.attr capability
            see getContext method   

        proc : Process, optional
            Process to use instead of the default one if any
            see getProc method     

        function : list, optional
            a list of command pair to be added to the setup.    

        **kwargs:  dict, optional
            all other key/pairs are passed to the setup function process,
            they are usually (but depend on the instrument SETUP command):
                expoId, noMove, check, noExposure

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

        cmdfunc = cmdfunc+function

        out = self.getProc(proc).setup(function=cmdfunc, **kwargs)

        self.onSetup.run(self)
        return out

    def qsetup(self, _values_=None, _include_=None, **kwargs):
        """ qsetup stand for quick setup do the same thing than setup

        Accept any key/val assignment. They are condition where this method cannot work
        so use setup instead, it is just a 'for lazy people' method.

        Note that qsetup send the setup for only the keywords provided in
        the function call (e.i.: equivalent to withvalue=False in setup function)
        
        For this function to work a default process must be defined.

        Parameters
        ----------
        **kwargs : dict, optional
            Could be
                - option to the process (e.g. timeout, expoId, etc)
                - key/value pair to send message. Key cannot be SETUP process option


        Examples
        --------
            qsetup( dit=0.01, ndit=1000, expoId=0, timeout=1000)
        is equivalent to:
            setup( {"DIT":0.01, "NDIT":1000}, expoId=0, timeout=1000)

        If the keyword exist in the FunctionDict it is used at it is
        otherwhise try with an upper case keyword.

                
            d.qsetup( dit=0.001, ndit=1000 )
        can also be decomposed:
            d["DIT"] = 0.001
            d["NDIT"] = 1000
            d.setup()

        """
        proc = self.getProc(None)
        # Remove all the option for the setup command
        pkeys = proc.commands["setup"].options.keys()+["timeout"]
        pkwargs = {k:kwargs.pop(k) for k in kwargs.keys() if k in pkeys}

        cmdfunc = self.qcmd(_values_, _include_=_include_, **kwargs)+pkwargs.pop("function",[])

        out = self.getProc(proc).setup(function=cmdfunc, **pkwargs)

        self.onSetup.run(self)
        return out

