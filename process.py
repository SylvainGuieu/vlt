from .mainvlt import Option
from .config  import config

msgSend_cmd = config.get("msgSend_cmd", "msgSend")


def getProc(proc=None):
    return proc if proc is not None else getDefaultProcess()


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


class Process(object):
    commands = {}
    _debug   = config.get("debug", False)
    _debugBuffer = None
    _verbose = config.get("verbose",1)
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

    def cmd(self, command, options=None, timeout=config.get("timeout",None)):
        options = options or {}
        if not command in self.commands:
            raise KeyError("command '%s' does not exists for this process"%(command))
        cmd = self.commands[command]
        return _timeout_( "%s %s"%(self.msg, cmd.cmd(options)), timeout)

    def cmdMsgSend(self, command, options=None, timeout=config.get("timeout",None)):
        options = options or {}
        return _timeout_("""%s "" %s"""%(self.msgSend_cmd, self.cmd(command,options)), timeout)

    def msgSend(self, command, options=None, timeout=None):
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




