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

buffreader  = Buffreader()

