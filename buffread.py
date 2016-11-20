"""
Define the Buffreader class.
"""

class Buffreader(object):
    """ 
    Buffreader class provide functions to read buffer. 
    All buffer reader function can take only one argument, the string buffer
    and return any object that reflect what is in the buffer.
    For instance the reader status (Which correspond to the process STATUS command) return 
        a dictionary of key/value pair dictionary reflecting the status. 

    """
    def getreader(self,cmd):
        cmd = cmd.lower()
        if cmd in self.__class__.__dict__:
            return self.__getattribute__(cmd)
        return self.general

    def general(self,buf):
        return buf

    def warning(self, msg, rtr=None):
        print "Warning ",msg
        return rtr

    def bufferLines(self, buf):
        sbuf = buf.split("\n")
        if sbuf[0].lstrip() != "MESSAGEBUFFER:":
            self.warning("Cannot find MESSAGEBUFFER: in output")
            return []
        sbuf.pop(0)
        return sbuf

    def expoid(self, buf):
        buf = self.bufferLines(buf)
        if len(buf)<1:
            self.warning("Cannot read expo Id in buffer output returned -1")
            return -1
        try:
            return int(buf[0])
        except:
            self.warning("Cannot read expoId as a int in %s"%(buf[0]))
            return -1
    setup = expoid
    wait  = expoid

    def status(self, buf):
        buf = self.bufferLines(buf)
        if not len(buf):
            return {}
        return self._status(buf[0])
    def status2(self,buf):
        return self._status(buf)

    def _status(self, buf, splitter=","):
        buf = buf.split(splitter)
        try:
            narg = int(buf[0])
        except:
            #self.warning("cannot read the number of key/val pairs")
            narg = -1
        if narg>-1:  buf = buf[1:None]
        if narg!=len(buf) and narg>-1:
            self.warning("expecting %d key/val pairs got %d "%(narg,len(buf)))

        output = {}
        for line in buf:
            sbuf = line.split(" ",1)
            if len(sbuf)<2:
                self.warning("key/pairs not found in %s on buffer %s"%(line,buf))
            else:
                sval = sbuf[1].lstrip()
                try:
                    val = int(sval)
                except:
                    try:
                        val = float(sval)
                    except:
                        val = sval.strip('"')
                output[sbuf[0].lstrip()] = val
        return output

    def state(self, buf):
        buf = self.bufferLines(buf)
        if not len(buf):
            self.warning("state values not understood")
            return (None,None)
        sbuf = buf[0].split("/")
        if len(sbuf)<2:
            return (buf, None)
        return tuple(sbuf)


    def error_structure(self, buf):
        """ read the error strcuture returned by e.g, msgSend """    
        pass


def paramproperty(k):
    def prop(self):
        return self.parameters.get(k, None)
    return property(prop)

class ErrorStructure(object):
    ##
    # read the line entirely for the following keywords
    _fulllines = ["Time Stamp", "Error Text", "Location"]
    ## 
    # keyword types, unknown will be str
    _types = {
        "Process Number":int, 
        "Error Number":int,
        "StackId": int, 
        "Sequence": int
    }
    def __init__(self, buffer):
        self.parameters = {}
        lines = [l for l in buffer.split("\n") if l.strip()]
        for line in lines:
            self._read_line(line.strip())
        self.origin = buffer    

    def _read_line(self, line):        
        if line[:2] == "--": # ignore ---------------- Error Structure -----------------
            return 

        key, _, val  = line.partition(":")
        key = key.strip()
        if not key:
            return 

        val = val.strip()

        if key in self._fulllines:
            self.parameters[key] = val
            return 
        val, _, rest = val.partition(" ")
        val = val.strip()
        rest = rest.strip()

        tpe = self._types.get(key, str)
        self.parameters[key] = tpe(val)
        if rest:
            return self._read_line(rest)
        return None
             
    TimeStamp = paramproperty("Time Stamp")        
    ProcessNumber = paramproperty("Process Number")
    ProcessName = paramproperty("Process Name")
    Environment = paramproperty("Environment")
    StackId = paramproperty("StackId")
    Sequence = paramproperty("Sequence")
    ErrorNumber = paramproperty("Error Number")
    Severity = paramproperty("Severity")
    Module = paramproperty("Module")
    Location = paramproperty("Location")
    ErrorText = paramproperty("Error Text") 
    
    def __repr__(self):
        return """
 ---------------- Error Structure ----------------
Time Stamp     : {0.TimeStamp}    
Process Number : {0.ProcessNumber}       Process Name : {0.ProcessName}            
Environment    : {0.Environment}   StackId  : {0.StackId}      Sequence : {0.Sequence}
Error Number   : {0.ErrorNumber}       Severity : {0.Severity}
Module         : {0.Module}      Location : {0.Location}
Error Text     : {0.ErrorText}
""".format(self)







buffreader  = Buffreader()

