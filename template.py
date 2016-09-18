from __future__ import print_function
from .mainvlt import dotkey, undotkey
from collections import OrderedDict

def openTsf(tsfname, path=None):
    filePath = findTsfFile(tsfname, path)
    tsf = TSF(filePath)
    tsf.parse()
    


def dict2param(name, d):
    ptype = d.get('TYPE', 'keyword')
    cls_lookup = {"number":NumberParam, "integer":IntegerParam, 
                  "keyword":KeywordParam, "coord":CoordParam, 
                  "boolean":BooleanParam, "string":StringParam
                  }
    try:
        cls = cls_lookup[ptype]
    except KeyError:
        raise ValueError("The Parameter type '%s' is not understood"%ptype) 
    return cls(name=name,  default=d.get('DEFAULT',None),   
            range=d.get("RANGE", None), 
            label=d.get("LABEL",""), minihelp=d.get("MINIHELP",""), 
            hide=d.get("HIDE", "")
            )   



class RangeError(ValueError):
    """ Error when a value is out of range """
    pass

class ParamRange(object):
    pass

class DumyRange(ParamRange):
    def __init__(self):
        pass

    def parse(self, value):
        return value

    @classmethod    
    def from_str(cl, st):
        raise RangeError("Cannot parse anything to a dummy range")  

class NumberRange(ParamRange):
    def __init__(self, mini, maxi):
        self.mini = mini
        self.maxi = maxi

    def parse(self, value):        
        if value<self.mini:
            raise RangeError("value must be >= %s, got %s"%(self.mini, value))  
        if value>self.maxi:
            raise RangeError("value must be <= %s, got %s"%(self.maxi, value))  
        return value

    @classmethod    
    def from_str(cl, st, type=float):   
        if not ".." in st:
            raise ValueError("Invalid range for NumberRange expecting 'min..max' got '%s'"%st)          
        mini, maxi = st.split("..")
        return cl(type(mini), type(maxi))

    def to_str(self):
        return "%s..%s"%(self.mini, self.maxi)  


class KeywordRange(ParamRange):
    def __init__(self, lst):
        self.lst = list(lst)        

    def parse(self, value):
        if value not in self.lst:
            lstsrt = " ".join("%r"%v for v in self.lst)
            raise RangeError("value must one of %s, got %s"%(lstsrt, value))
        return value

    @classmethod    
    def from_str(cl, st, type=str): 
        lst = [type(v) for v in st.split(" ") if v]
        return cl(lst)

    def to_str(self):
        return " ".join([str(v) for v in self.lst])


class BooleanRange(KeywordRange):

    @classmethod    
    def from_str(cl, st, type=str): 
        lst = [type(v) for v in st.split(" ") if v]

        return cl([True if v is "T" else False for v in lst] )


class CoordRange(ParamRange):
    def __init__(self, coordtype):
        coordtype = coordtype.lower()
        lookup = ["ra", "dec"]
        if coordtype not in lookup:
            raise ValueError("Invalid Range for coord expecting one of %s got '%s'"%(" ".join("%r"%l for l in lookup), coordtype))

    def parse(self, value):
        ## :TODO: make the coordinate parser 
        print("WARNING coordinate parser not yet implemented")
        return value

    @classmethod    
    def from_str(cl, st):
        return cl(st) 

class TemplateSignatureParam(object):
    """ Template Param object hold Param definition and value/range parser """
    _range   = None
    _default = None
    _miniHelp = ""
    _hide = ""
    

    def __init__(self, name="", type="", default=None,  
                 range=None, 
                 label="", minihelp="", hide=""):
        self.setName(name)      
        self.setRange(range)
        self.setDefault(default)
    
    ## heart of the object type parser 

    ## list of range classes excepted by this Parameter 
    _range_classes = [ParamRange]
    def _parse_type(self, value):
        return str(value)

    def _parse_range(self, value):
        try:
            newval = self.range.parse(value)    
        except RangeError as e:
            raise RangeError("When parsing '%s' for key '%s' : %s"%(value, self.name, e)) 
        return newval    
            
    def parse(self, value):
        value = self._parse_type(value)
        value = self._parse_range(value)
        return value        

    def match(self, pattern):
        patterns = dotkey(pattern).split(".")
        keys = self.name.split(".")
        shortkeys = keys[0:len(patterns)]
        return shortkeys==patterns, ".".join(keys[len(patterns):])


    #############################
    # name      
    def setName(self, name):
        self._name = dotkey(str(name))
    def getName(self):
        return self._name
    @property
    def name(self):
        return self.getName()
    @name.setter
    def name(self, name):
        self.setName(name)
        
    #############################
    # default   
    def setDefault(self, default):
        try:
            self._default = self.parse(default)
        except RangeError:
            print ("Warning default value %r of '%s' is out of range"%(default,self.name))            

        return 
        try:
            self._default = self._parse_range(default)
        except Exception as e:
            print("When trying to set default as '%s'"%default)
            raise e 
    def getDefault(self):
        return self._default
    @property
    def default(self):
        return self.getDefault()
    @default.setter
    def default(self, default):
        self.setDefault(default)

    #############################
    # minihelp  
    def setMiniHelp(self, miniHelp):
        self._miniHelp = str(miniHelp)
    def getMiniHelp(self):
        return self._miniHelp
    @property
    def miniHelp(self):
        return self.getMiniHelp()
    @miniHelp.setter
    def miniHelp(self, miniHelp):
        self.setMiniHelp(miniHelp)  

    #############################
    # label     
    def setLabel(self, label):
        self._label = str(label)
    def getLabel(self):
        return self._label
    @property
    def label(self):
        return self.getLabel()
    @label.setter
    def label(self, label):
        self.setLabel(label)    

    #############################
    # hide      
    def setHide(self, hide):
        self._hide = str(hide)
    def getHide(self):
        return self._hide
    @property
    def hide(self):
        return self.getHide()
    @hide.setter
    def hide(self, hide):
        self.setHide(hide)          

    #############################
    # range     
    def setRange(self, range):
        if range is None:
            self._range = DumyRange()
            return 
        elif range is tuple:
            if len(range)!=2:    
                raise ValueError("range must be None, a 2 tuple or a list")         
            self._range = NumberRange(*range)
            return 
        elif hasattr(range,"__iter__"):
            self._range = KeywordRange(range)

        elif isinstance(range, basestring):
            for cl in self._range_classes:
                try:
                    rg = cl.from_str(range)
                except ValueError:
                    continue    
                else:
                    range = rg
                    break
            else:
                raise ValueError("Invalid string range '%s' for '%s'"%(range, self.name))           
            self._range = range                
            return     
        elif isinstance(range, ParamRange):
            self._range = range
            return 
        raise ValueError("range must be None, a 2 tuple, a list or a ParamRange instance got a '%s'"%type(range))                           

    def getRange(self):
        return self._range

    @property
    def range(self):        
        return self.getRange()

    @range.setter
    def range(self, range):
        self.setRange(range)    
    

class NumberParam(TemplateSignatureParam):
    _range_classes = [NumberRange, KeywordRange]
    def _parse_type(self, value):
        return float(value)

class IntegerParam(TemplateSignatureParam):
    _range_classes = [NumberRange, KeywordRange]
    def _parse_type(self, value):
        return int(value)

class KeywordParam(TemplateSignatureParam):
    _range_classes = [KeywordRange]
    def _parse_type(self, value):
        return str(value)


class StringParam(TemplateSignatureParam):
    _range_classes = [KeywordRange]
    def _parse_type(self, value):
        return str(value)


class KeywordListParam(TemplateSignatureParam):
    _range_classes = [KeywordRange]
    def _parse_type(self, value):
        if isinstance(value, basestring):
            value = [str(v) for v in value.split(" ") if v]
        else:
            value = [str(v) for v in value] 
        return value
    def _parse_type(self, value):
        if isinstance(value, basestring):
            value = [str(v) for v in value.split(" ") if v]
        value = [self.range.parse(v) for v in value]
        return value

class KeywordListParam(TemplateSignatureParam):
    _range_classes = [KeywordRange]
    def _parse_type(self, value):
        if isinstance(value, basestring):
            value = [str(v) for v in value.split(" ") if v]
        else:
            value = [str(v) for v in value] 
        return value
    def _parse_type(self, value):
        if isinstance(value, basestring):
            value = [str(v) for v in value.split(" ") if v]
        value = [self.range.parse(v) for v in value]
        return value


class CoordParam(TemplateSignatureParam):
    _range_classes = [CoordRange]
    def _parse_type(self, value):
        return str(value)

class BooleanParam(TemplateSignatureParam):
    _range_classes = [BooleanRange]
    def _parse_type(self, value):
        return bool(value)



class TemplateSignature(OrderedDict):
    def __init__(self, *args, **kwargs):
        header = kwargs.pop("header", {})
        info = kwargs.pop("info", {})
        super(TemplateSignature, self).__init__(*args, **kwargs)
        for key, param in self.iteritems():
            if not isinstance(param, TemplateSignatureParam):
                raise ValueError("all items value should be of instance TemplateSignatureParam got a '%s'"%(type(param)))
        self._header = header
        self._info = info

        
    def __getitem__(self, item):
        item = dotkey(item)
        try:
            return super(TemplateSignature,self).__getitem__(item)
        except KeyError:
            for param in self.itervalues():
                if item == param.name:
                    return param
        raise KeyError("%r"%item)    

    def __contains__(self, item):
        item = dotkey(item)
        if super(TemplateSignature,self).__contains__(item):
            return True
        for param in self.itervalues():
            if item == param.name:
                return True
        return False


    @classmethod
    def from_dict(cls, parameters, header={}):       
        parameters  = parameters.copy()                
        tplinfo = parameters.pop("TPL", {})    
        parameters = [(key,dict2param(key,param)) for key,param in parameters.iteritems()]    
        return cls(parameters, header=header, info=tplinfo) 
            
    @property
    def info(self):
        return self._info
            

    @property
    def header(self):
        return self._header                     
            
    def _copy_attr(self, new):
        d = dict(self.__dict__)
        d.pop('_OrderedDict__root', None)
        d.pop('_OrderedDict__map' , None)
        new.__dict__.update(d)
        return new

    def restrict(self, patter_or_list):        
        items = []
        if isinstance(patter_or_list, basestring):
            pattern = patter_or_list
            for key, param in self.iteritems():
                match, shorkey = param.match(pattern)
                if match:
                    items.append( (shortkey, param))
        else:
            lst = patter_or_list
            for key in lst:
                items.append( (key, self[key]) )         
        new = self.__class__(items)        
        self._copy_attr(new)
        return new








class ObdParam(object):
    """ OBD Parameter is a TemplateSignatureParam with Value """
    def __init__(self, param, value):
        self._param = param
        self._value = param.parse(value)

    @property
    def param(self):
        """ Value Paramter """
        return self._param
    
    def __str__(self):
        return """{0}="{1}" """.format(self.name, self.value)   

    def __repr__(self):
        return """{0:25}\t{1!r} """.format(self.name, self.value)


    def setValue(self, value):
        self._value = self.param.parse(value)

    def getValue(self):
        return self._value if self._value is not None else self.param.default   

    @property
    def value(self):
        return self.getValue()

    @value.setter
    def value(self, value):
        self.setValue(value)

    @property
    def name(self):
        return self.param.name

    def hasValue(self):
        """ True if OB Param has a value set """
        return self.value is not None           

    def match(self, pattern):
        return self.param.match(pattern)    
        


class Obd(list):


    def __init__(self, templates, info={}):
        super(Obd,self).__init__(templates)
        self._info = info

    def __getitem__(self, item):                             
        value = super(Obd,self).__getitem__(item)
        if isinstance(value, ObdTemplate):
            return value 
        return self.__class__(value, info=self._info.copy())    

    def __setitem__(self, item, tpl):
        if not isinstance(tpl, ObdTemplate):
            raise ValueError("item must be of instance ObdTemplate got a '%s'"%(type(tpl)))    
        super(Obd, self).__setitem__(item, tpl)
    
    def __repr__(self):
        return "\n\n".join("%r"%tpl for tpl in self)    

    def append(self, tpl):
        if not isinstance(tpl, ObdTemplate):
            raise ValueError("item must be of instance ObdTemplate got a '%s'"%(type(tpl)))
        super(Obd, self).append(tpl)

    def extend(self, tpls):
        for tpl in tpls:
            if not isinstance(tpl, ObdTemplate):
                raise ValueError("all items must be of instance ObdTemplate got one '%s'"%(type(tpl)))                    
        super(Obd, self).extend(tpl)            

    def restrict(self, name_or_list):
        if isinstance(name_or_list, basestring):
            return self.__class__( [tpl for tpl in self if tpl.match(name_or_list)], self._info.copy())    
        else:
            return self.__class__( [self[index] for index in name_or_list], self._info.copy())        
            

class ObdTemplate(OrderedDict):
    def __init__(self, id, name, obdParams, info={}):
        super(ObdTemplate, self).__init__(obdParams)
        self._id = id
        self._name = name
        self._info = info

        for key, value in self.iteritems():
            if not isinstance(value, ObdParam):
                raise ValueError("All params items must be ObdParam object")
        
    def __getitem__(self, item):
        item = dotkey(item)
        try:
            return super(ObdTemplate, self).__getitem__(item)
        except KeyError:
            for param in self.itervalues():
                if item == param.name:
                    return param
        raise KeyError("%r"%item)

    def __setitem__(self, item, value):
        super(ObdTemplate, self).__setitem__(dotkey(item),value)

    def __contains__(self, item):
        item = dotkey(item)
        if super(ObdTemplate, self).__contains__(item):
            return True
        for param in self.itervalues():
            if item == param.name:
                return True
        return False

    def __repr__(self):
        text = """###### {self.id} {self.name} ###### \n""".format(self=self)
        for key, param in self.iteritems():
            key = "[%s]"%key
            text += """    {key:27}    {param!r}\n""".format(key=key,param=param)
        return text    

    def __str__(self):
        super(ObdTemplate, self).__str__()    

    @property
    def info(self):
        return self._info
        
    # def get(self, item , default):
    #     return self.params.get(item, default)

    # def update(self, __d__={}, **kwargs):
    #     return self.params.update(__d__, **kwargs)

    # def keys(self):
    #     return self.params.keys()

    # def values(self):
    #     return self.params.values()

    # def items(self):
    #     return self.params.items()
    
    # def iterkeys(self):
    #     return self.params.iterkeys()

    # def itervalues(self):
    #     return self.params.itervalues()

    # def iteritems(self):
    #     return self.params.iteritems()      

    # def match(self, name):
    #     self.name == name    

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def params(self):
        return self._params
        
    def restrict(self, name_or_list):        
        if isinstance(name_or_list, basestring):
            outitems = []
            for key, param in self.iteritems():
                match, shortkey = param.match(name_or_list)
                if match:
                    outitems.append((shortkey, param))
            return self.__class__( self.id, self.name, OrderedDict(outitems), self.info.copy())        

        else:
            return self.__class__( self.id, self.name, {key:self[keys] for key in name_or_list}, self.info.copy())

    
        
