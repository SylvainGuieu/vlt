import re
from .keywords import KeywordFile

def _start_header(f, key, value, more):
        f.start_header()
        return f.parse_line(more)

def _end_header(f, key, value, more):
        f.end_header()
        return f.parse_line(more)

def _new_param(f, key, value, more):
    f.parameters[value] = {}
    return f.parse_line(more)

def _isisf(value):
    return value[0:4] == "ISF "

def _isfvalue(f, value):
    isfvalue = value[4:]
    if f.isf is None or (not isfvalue in f.isf):
        f.say("ISF linked value left has it is for %s " % value)
        return value
    return f.isf[isfvalue]


class TSF(KeywordFile):
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
        "TPL.PARAM": _new_param
    }
    value_cases = {
        _isisf:_isfvalue
    }

    def __init__(self, *args, **kwargs):
        isf = kwargs.pop("isf", None)
        super(TSF,self).__init__(*args, **kwargs)
        if isinstance(isf, basestring):
            isf_file = ISF(isf)
            isf_file.parse()
            self.isf = isf_file.parameters
        else:
            self.isf = isf

    def key2path(self, key):
        keys = key.split(".")
        N = len(keys)
        if N<2:
            return keys[0], None
        return ".".join(keys[0:-1]), keys[-1]

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

class ISF(TSF):
    # same as TSF except that value are stacked in a flat dictionary
    value_keys = {}
    def key2path(self, key):
        return [key]

