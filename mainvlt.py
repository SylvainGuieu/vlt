#!/usr/bin/python
import os
import commands
import re

from .config import config


msgSend_cmd = "msgSend"
debug = not os.getenv("HOST")  in ["wbeti" , "wpnr" , "wbeaos"]

verbose = 1
_defaultProcess = None

LASTBUFFER = ""
DEFAULT_TIMEOUT = None

KEY_MATCH_CASE = False


############################################################
# Some functions which are used as dtype or format
############################################################

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


def getProc(proc=None):
    return proc if proc is not None else getDefaultProcess()


def formatBoolFunction(value):
    """
    return "T" or "F" if the input boolean value is True or False.
    Used to format VLT message command
    """
    if value:
        return "T"
    return "F"


def formatBoolCommand(value):
    """ this return an empty string.
    Used to format boolean values in commands, they do not accept
    argument
    """
    # command does not accept argument when they are boolean
    return ""


class Option(object):
    """
    Option class for VLT command.
    Option have is a pair of key (or message) and value

    for instantce in:
        msgSend "" pnoControl SETUP "-function DET.DIT 0.005 DET.NDIT 1000 -expoId 0"

    'function' and 'expoId' are Option

    p = Option(msg, dtype)
    """
    default = None
    format  = "%s"
    def __init__(self, msg, dtype , format="%s", default=None, name=""):
        self.name  = name #not used
        self.msg   = msg
        self.dtype = dtype
        if default is not None:
            self.default = self.parseValue(default)
        self.format= format

    def __str__(self):
        if self.default is None:
            dfs = "None"
        else:
            default = self.getDefault()
            if issubclass(type(default), str):
                dfs = "'%s'"%(self.getFormatedDefault())
            else:
                dfs = self.getFormatedDefault()
        return """%s("%s", %s, default=%s, format="%s")""" % (self.__class__.__name__, self.msg, self.dtype, dfs, self.format)

    def __repr__(self):
        return self.__str__()

    def cmd(self, value=None):
        if value is None:
            value = self.default
        msg = self.msg
        return cmd((msg, self.formatValue(value)))

    def getDefault(self):
        """ Return the default value for this Option """
        return self.parseValue(self.default)

    def setDefault(self, value):
        """ Set the default value for this Option """
        self.default = self.parseValue(value)

    def getFormatedDefault(self):
        """ return the fromated defaultValue if any """
        if self.default is None:
            return ""
        return self.formatValue(self.default)

    def parseValue(self, value):
        """ Parse the value according to the dtype of this Option
        The parsed value is returned.
        e.g:
        o = Option("expoId",int)
        o.parse("45") # return int(45)
        """
        try:
            return self.dtype(value)
        except ValueError:
            raise ValueError("Cannot convert '%s' to the expecting type %s for param '%s'"%(value,self.dtype, self.msg))

    def formatValue(self, value):
        """ Parse and format value according to the dtype and format """
        value = self.parseValue(value)
        # format can be a string or a function
        if issubclass(type(self.format), str):
            return self.format%(value)
        else:
            return self.format(value)


class FunctionIter:
    def __init__(self, function):
        self.function = function
        self.indexes = function._getAllIndexes()
        self.counter = -1
        self.size = len( self.indexes)
    def next(self):
        self.counter += 1
        if self.counter >= self.size:
            raise StopIteration("out of range")
        return self.function[self.indexes[self.counter]]


class EmbigousKey(KeyError):
    pass


def cmd2Option(msg,fromdict=None):
    return Function.newFromCmd(msg, fromdict=fromdict)


def cmd2Function(msg, fromdict=None):
    return Function.newFromCmd(msg, fromdict=fromdict)


def dotkey(key):
    return ".".join( key.split(" ") )


def undotkey(key):
    return ".".join( key.split(" ") )


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


def processClass(processname, path=None):
    """
    Return the dynamicaly created python class of a process

    The program look for the file processname.cdt into the list of path
    directories wich can be set by the path= keyword.
    By default config["cdtpath"] is used
    """
    import cdt
    fileName = cdt.findCdtFile(processname+".cdt", path)
    pycode = cdt.Cdt(fileName).parse2pycode()

    exec pycode
    # the pycode should contain the variable proc
    # witch is the newly created object
    return cls


def openProcess(processname, path=None):
    """
    return processClass(processname, path)()

    e.g.:
      pnoc = openProcess("pnoControl")
      pnoc.setup( function="INS.MODE ENGENIERING DET.DIT 0.01" )

    """
    return processClass(processname, path)()

    # pyfile = cdt.Cdt(fileName).parse2pyfile()
    #
    # mod = __import__("vlt.processes."+processname,
    #                  fromlist=[processname])
    # reload(mod) #in case cdt changed
    # return mod.proc


def vltbool(val):
    return bool( val!='F' and val!=False and val)


def readDictionary(dictFileSufix, path=None):
    import dictionary


    dfileName = dictionary.findDictionaryFile(dictFileSufix, path)
    dfile = dictionary.Dictionary(dfileName)
    dfile.parse()
    return dfile.to_functionDict()

class VLTError(Exception):
    pass

class Process(object):
    commands = {}
    _debug   = debug
    _debugBuffer = None
    _verbose = verbose
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

    def cmd(self, command, options=None, timeout=DEFAULT_TIMEOUT):
        options = options or {}
        if not command in self.commands:
            raise KeyError("command '%s' does not exists for this process"%(command))
        cmd = self.commands[command]
        return _timeout_( "%s %s"%(self.msg, cmd.cmd(options)), timeout)

    def cmdMsgSend(self, command, options=None, timeout=DEFAULT_TIMEOUT):
        options = options or {}
        return _timeout_("""%s "" %s"""%(self.msgSend_cmd, self.cmd(command,options)), timeout)

    def msgSend(self, command, options=None, timeout=DEFAULT_TIMEOUT):
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


class Cmd(list):
    def __add__(self, right):
        return cmds(self, right)

    def __addr__(self, left):
        return cmds(left, self)

def cmd(st):
    """
    From a string or list or list of tuple return a flat list of valid
    command frunction/key pair

    > cmd(  ("DET.DIT", 0.003) )
    [('DET', 'DIT')]
    > cmd( [ ("DET.DIT",0.001), [[("DET.NDIT",100)]]] )
    [('DET.DIT', 0.001), ('DET.NDIT', 100)]
    """
    if issubclass(type(st), (list)):
        # Always return a flat list
        cmds = []
        for c in st:
            cmds += cmd(c)
        return Cmd(cmds)
    #this is always a flat list
    return Cmd([st])

def cmd2str(tcmd):
    tcmd = cmd(tcmd) # make a flat list

    out  = []
    for c,v in tcmd:
        if isinstance(v, str) and v.find(" ")>-1:
            v = "'{}'".format(v)
        out.append( "{} {}".format(c,v))
    return " ".join(out)

def cmds(*args):
    output = []
    for a in args:
        output += cmd(a)
    #
    # Return the list and elimiminate duplicate
    return Cmd(dict(output).items())


class Params(dict):
    def __init__(self, *args, **kwargs):
        super(Params,self).__init__(*args, **kwargs)
        for p,v in self.iteritems():
            if not issubclass(type(v),Param):
                raise TypeError("Params Accept only Param type got %s"%(type(v)))


class System(object):
    # a list of function of the system
    # e.g. for a detector
    #    functions = {
    #             'dit'  :Function("DET.DIT"  , float, "%f", 0.0 ),
    #             'ndit' :Function("DET.NDIT" ,  long, "%d", 10  ),
    #             'polar':Function("DET.POLAR", int , "%04d", 0),
    #
    #             'type':Function( "DPR.TYPE", str , "%s", "TEST" ),
    #             'tech':Function( "DPR.TECH", str , "%s", "image"),
    #             'imgname':Function( "OCS.DET.IMGNAME", str , "%s", "IMG_{type}"),
    #
    #             'mode':Function( "INS.MODE", str , "%s", "ENGINEERING" ),
    #             'readoutmode':Function("INS.READOUT.MODE", str , "%s", "DOUBLE")
    #         }
    #functions = FunctionDict({})
    # a list of mendatory functions for instance "INS.MODE"

    # a list of function for wich the value should be rebuild from others function
    # for instance rebuild = ["type","imgname"] , order matter
    # type and then imgname will be rebuilt if e.g.
    #  type = "BIAS-{polar}"  # {polar} will be replaced by the value of polar
    #  imgname = "INSTRUMENT-{type}_" # {type} will be replaced by the previously rebuilt type
    rebuild = []
    module  = True
    counter = 0
    def __init__(self, proc):
        self.proc = proc

    def __setitem__( self, item, value):
        # set the item in the self.function
        self.functions[item] = value
    def __getitem__( self, item):
        # return the item inside the functiondic
        return self.functions[item]
    def __iter__(self):
        # return the functionsDict as iterator
        return self.functions.__iter__()
    def __contains__(self, item):
        # return the functionsDict as iterator
        return self.functions.__contains__(item)
    def __format__(self, fmt_spec):
        # return the functionsDict as iterator
        return self.functions.__format__(fmt_spec)
    def copy(self):
        new = self.__class__(self.proc)
        new.functions = self.functions.copy(True)
        return new

    def iteritems(self):
        return self.functions.iteritems()
    def iterkeys(self):
        return self.functions.iterkeys()
    def items(self):
        return self.functions.items()
    def keys(self):
        return self.functions.keys()
    def pop(self, *args):
        return self.functions.pop(*args)
    def setdefault(self, *args):
        return self.functions.setdefault(*args)


    def new(self, *args, **kwargs):
        kwargs = kwargs or {}
        new = self.__class__( self.proc)
        new.function  = self.functions.copy(True) # make a deep copy

        new.update(*args, **kwargs)
        return new

    def get(self, key, default=False):
        return self.functions[key].get(default)

    def set(self, key , val):
        self.functions[key] = val

    def update( self, *args, **kwargs):
        return self.functions.update( *args, **kwargs)

    def cmd(self, *args, **kwargs):
        self = self.copy()
        vals = self.functions#.copy()
        vals.update(*args, **kwargs)
        vals = vals.rcopy()
        #for k in self.mandatory:
        #    if not vals[k].hasValue():
        #        self.set( k, vals[k].get(True)) # copy is default to value for mandatory

        cmds = vals.cmd(context = self)
        return cmd(cmds)

    def sequence(self, method, *args, **kwargs):
        if issubclass(type(method), str):
            method = self.__getattribute__(method)
        elif not hasattr(self, "__call__"):
            raise TypeError("Method shoud have a __call__ method")
        return Sequence( ( method, args, kwargs) )

    def setup(self, kwargs=None , expoId=0, timeout=None):
        kwargs = kwargs or {}
        return self.proc.msgSend("setup", dict(function=self.cmd(kwargs), expoId=expoId), timeout= timeout)



class Instrument(Process):

    def __init__(self, init=True):
        self._init_dictionaries

    def _init_dictionaries(self):
        pass



