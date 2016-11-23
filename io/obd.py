import re
from .keywords import KeywordFile
from .tsf import openTemplateSignature
from collections import OrderedDict
from ..template import ObdParam, ObdTemplate, Obd
from ..config import config
from . import ospath
######
## already opened templates 
TEMPLATES = {}


def _start_header(f, key, value, more):
        f.start_header()
        return f.parse_line(more)

def _end_header(f, key, value, more):
        f.end_header()
        return f.parse_line(more)

def _new_template(f, key, value, more):   
    f.template = OrderedDict([(key,value)])
    f.parameters[f.template_counter] = f.template
    f.cdict = "template"
    f.template_counter += 1
    return f.parse_line(more)

class OBD(KeywordFile):
     # match : INS.FILT1.RANGE "value"; # more stuff
    _c1 = """[ \t]+["]([^"]*)["][ \t]*[;](.*)"""
    # match : INS.FILT1.RANGE "value" # comment
    _c2 = """[ \t]+["]([^"]*)["]().*"""
    # match :  INS.FILT1.RANGE value; # more stuff
    _c3 = """[ \t]*([^;#" \t]+)[ \t]*[;](.*)"""
    # match :  INS.FILT1.RANGE value # comment
    _c4 = """[ \t]*([^;#" \t]+)().*"""
    # match : PAF.HDR.START; #more stuff
    _c5 = """[ \t]*[;]()(.*)"""
    # match : PAF.HDR.START # comment
    _c6 = """[ \t#]?.*()()"""
    reg = re.compile("""^([^ \t;#]+)({c1}|{c2}|{c3}|{c4}|{c5}|{c6})$""".format(
                    c1=_c1, c2=_c2, c3=_c3, c4=_c4, c5=_c5, c6=_c6
                    )
                    )
    cases = {
        # func of signautre (f, key, value, more)
        "PAF.HDR.START": _start_header,
        "PAF.HDR.END": _end_header,
        "TPL.ID": _new_template, 
    }
    value_cases = {        
    }
    def __init__(self, *args, **kwargs):
        super(OBD, self).__init__(*args, **kwargs)
        self.parameters = OrderedDict()        
        self.template = None
        self.template_counter = 0

    def match_line(self, line):
        m = self.reg.match(line.strip())
        if not m:
            return None, None, None
        groups = m.groups()
        gi = range(2,14,2)# [2,4,6,8, ...]
        for i in gi:
            if groups[i] is not None:
                return groups[0], groups[i], groups[i+1]
        raise Exception("BUG none of the group founf in match")    

def findObdFile(file_name, path=None,  prefix=None, extention=None):
    """
    find the tsf file_name inside the path list.
    by default path list is config["tsfpath"]
    """
    return ospath.find(file_name, path=path, prefix=prefix, extention=extention, 
                        defaults=config['obd']
                      )

def openObd(file_name, path=None,  prefix=None, extention=None):
    obd_file = ospath.find(file_name, path=path, prefix=prefix, extention=extention, 
                        defaults=config['obd']
                      )

    f = OBD(obd_file)
    f.parse()
    obd = f.parameters
    obdtemplates = []
    for i in range(f.template_counter):
        tpl_dict = obd.pop(i)
        tpl_id   = tpl_dict.pop("TPL.ID", None)
        tpl_name = tpl_dict.pop("TPL.NAME", None)

        if not tpl_id:
            raise ValueError("cannot find a TPL.ID for template #%d"%i)

        if tpl_id in TEMPLATES:
            tpl = TEMPLATES[tpl_id]                      
        else:
            try:
                tpl = openTemplateSignature(tpl_id)
            except IOError as e:
                raise IOError("Ob is attached to a tsf that cannot be opened : %s "%e)
            TEMPLATES[tpl_id] = tpl


        #info = {key:obd.pop(key) for  key, val in obd.items() if key.startswith("OBS.")}

        parameters = {key:ObdParam(tpl[key], val) for key, val in tpl_dict.iteritems()}
                
        obdtpl = ObdTemplate(tpl_id, tpl_name, parameters)

        obdtemplates.append(obdtpl)

    return Obd(obdtemplates, info=obd, path=obd_file)    
            



    
