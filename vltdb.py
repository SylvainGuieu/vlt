import os
import commands
import re
import numpy as np

_db_write_cmd = "dbWrite"
_db_read_cmd = "dbRead"

_db_types_convertion = {
    "INT32/UINT32":np.int32, 
    "BYTES":str, 
    "LOGICAL":int
}

def get_type(strtype):
    if strtype in _db_types_convertion:
        return _db_types_convertion[strtype]
    
    if hasattr( np, strtype.lower()):
        return np.__getattribute__( strtype.lower() )
    
    raise TypeError("Type \"{0}\" unknown ".format(strtype))
def convert_value(strtype, value):
    return get_type(strtype)(value)


class db(object):
    debug = False
    verbose = True
    def __init__(self,name):
        self.name = name
        
    def writeList(self, addrs=None, var=None, index=0, values=None):
        addrs  = addrs or []
        var    = var or ""        
        values = values or []
        tps = self.readTypes( addrs, "{0}({1})".format(var, index) )
        if len(tps)!= len( values):
            raise ValueError("got %d type in data base for %d values"%(len(tps),len(values)))
        i = 0
        for t,v in zip(tps, values):
            self.write( addrs, "{0}({1},{2})".format(var,index, i), t(v))
        return None
    
    def writeDict(self, addrs=None, var=None, index=0, values=None):
        addrs  = addrs or []
        var    = var or ""        
        values = values or {}
        for k,v in values.iteritems():
            self.write( addrs, "{0}({1},{2})".format(var,index, k), v)

    
    def cmdWrite(self, addrs=None, var=None, value=None):
        addrs = addrs or []
        var  = var or ""
        
        if isinstance( value, str):
            svalue = "\"{0}\"".format(value)
        else:
            svalue = "{0}".format(value)
        
        return """{cmd} "{0}:{1}:{2}" {3}""".format(self.name, ":".join(addrs), var, svalue, cmd=_db_write_cmd) 
    def write(self,addrs=None, var=None, value=None ):

        cmdLine = self.cmdWrite( addrs, var=var, value=value)
        if self.debug:
            print cmdLine
            return ""
        if self.verbose:
            print cmdLine

        
        status, output = commands.getstatusoutput(cmdLine)
        return output
    

    
        
    def cmdRead( self, addrs=None, var=None):        
        addrs = addrs or []
        var  = var or ""
        return """{cmd} \"{0}:{1}:{2}\"""".format(self.name, ":".join(addrs), var, cmd=_db_read_cmd)
    
    def read(self,addrs, var=None):
        cmdLine = self.cmdRead( addrs, var=var)
        if self.debug:
            print cmdLine
            return []
        if self.verbose:
            print cmdLine
        
        status, output = commands.getstatusoutput(cmdLine)
        return self.readBuffer(output)

    def readTypes(self, addrs, var=None):
        cmdLine = self.cmdRead( addrs, var=var)
        if self.debug:
            print cmdLine
            return []        
        status, output = commands.getstatusoutput(cmdLine)
        return self.readBufferTypes(output)
        
    
    _re_read_buffer = re.compile("([^ ]+)[ ]+value[ ]+=[ ]*(.+)") 
    def readBuffer( self, buff):
        lbuff = buff.split("\n")
        out = []
        for l in lbuff:
            matches = self._re_read_buffer.findall( l)
            for m in matches:
                out.append( convert_value(m[0].strip(), m[1].strip()) )
        return out    
    def readBufferTypes( self, buff):
        lbuff = buff.split("\n")
        out = []
        for l in lbuff:
            matches = self._re_read_buffer.findall( l)
            for m in matches:
                out.append( get_type(m[0].strip()) )
        return out
