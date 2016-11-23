import re
import os
from ..config import config
from ..function import  Function
from ..functiondict import FunctionDict
from ..mainvlt import cmd
from . import ospath
from collections import OrderedDict

cdtconfig = config["cdt"]
cdtpydir = cdtconfig["pydir"]
debug = cdtconfig["debug"]

indentStr = "    "  # python indent string. Do not change that






vltModuleImport = """from vlt.process import Process, Param, Command;from vlt.mainvlt import formatBoolCommand"""

generalMouleImport ="""
from collections import OrderedDict
"""
vltModulePref   = ""  # The prefix for vlt module, used to call vlt functions

cdtModuleImport = "from vlt.io import cdt"
cdtModulePref = "cdt."  # The prefix for this module, used to call vlt functions

# submodule and class name for buffer reader
buffreadModuleImport = "from vlt.buffread import buffreader"
buffreadClassName = "buffreader"


# Some parameters need special treatment before returned to msgSend
# like function
# which can accept as argument a list of tuple:
#    [("cmd1","opt1"),("cmd2","opt2"), ...]
# Add the functions string name in this directory
typeExeption = {
    "": {  # default ones
        "function": cdtModulePref+"dtypeFunctionList",
        "params": cdtModulePref+"dtypeFunctionList"
        },
    "status": {  # specific to command status
        "function": cdtModulePref+"dtypeFunctionListMsg"
    }
}

def msg_send_decorator(msg, commands):
    options = commands[msg].options
    def tmp(self, *args, **kwargs):
        for arg, option in zip(args,options):
            if option in kwargs:
                raise TypeError("got multiple values for keyword argument '%s'"%option)
            kwargs[option] = arg    
        timeout = kwargs.pop("timeout", None)        
        return self.msgSend(msg, kwargs, timeout=timeout)            
    tmp.__doc__ = form_cmd_help(msg,commands[msg])
    return tmp

def form_cmd_help(msg,command):
    return msg+"("+" ,".join(k+"=%s"%o.dtype for k,o in command.options.iteritems())+")\n\n"+command.helpText


def dtypeFunctionList(function):
    """
    write a command line based on an array of tuple :
      [("cmd1","opt1"),("cmd2","opt2"), ...]
    or an array of string ["cmd1 opt1", "cmd2 opt2", ...]
    e.g:
       dtypeFunctionList ( [("cmd1","opt1"),("cmd2","opt2"), ...])
       will return "cmd1 opt1 cmd2 opt2 ..."
    This function is used for instance in message send command

    if the unique argument is a str, it is returned as it is.
    argument can also be a FunctionDict or a System object, in this case
    the command for all functions with a values set is returned.
    """
    if issubclass(type(function), str):
        return function
    if issubclass(type(function), (FunctionDict,)):
        return "{}".format(function)
    if issubclass(type(function), Function):
        return dtypeFunctionList(function.cmd())

    function = cmd(function) #to make sure it is a flat list
    out = []
    for func in function:
        if issubclass( type(func), tuple):
            if len(func)!=2:
                raise TypeError("Expecting only tuble of dim 2 in setup list")
            if isinstance( func[1], str):
                fs = func[1].strip()
                if fs.find(" ")>-1:
                    out.append("%s '%s'"%(func[0],fs))
                else:
                    out.append("%s %s"%(func[0],fs))
            else:
                out.append("%s %s"%func)
        else:
            out.append("%s"%(func))
    return " ".join(out)


def dtypeFunctionListMsg(function):
    if issubclass( type(function), str) :
        return function
    if issubclass( type(function), (FunctionDict)):
        return " ".join( [f.getMsg() for f in function] )
    if issubclass( type(function), (Function)):
        return function.getMsg()
    return " ".join(function)



class Cdt(file):
    """
    A file description parser for CDT ESO files.
    the Cdt class is derived from the python file object

    # parse the file and return a string of python code containing
    # the new class definition
    f.parse2pycode(className="pnoControl")


    # parse and write the python class definition in a file
    parse2pyfile(fileName="pnoControl.py", lassName="pnoControl")


    """
    indentSize = 4
    indent = 0
    
    commands = {}
    cte = {}

    curentParameter = None
    curentParameters = None
    debug = []

    def parse(self, line=None, count=0):
        if debug:
            if line is not None:
                self.debug += ["|"+line.rstrip()+"|"]

        if line is None:
            if debug:
                self.debug += [">>> line is None"]
            line = self.readline()



        while len(line):
            if debug:
                self.debug += [">>> End of file"]
            count += 1

            # empty line just continue
            if not len(line.strip()):
                line = self.readline()
                continue
            stline = line.lstrip()

            # comment line (do actually nothing)
            if stline[0:2] == "//":
                line = self.commentLine(line)
                continue

            #  include line mut include the new file
            #  on place
            if stline[0:8] == "#include":
                line = self.includeLine(line)
                continue

            #  all other type of lines are handled
            #  by commandLine
            line = self.commandLine(line)

        return count

    def parse2dict(self):
        """ Parse the CDT file and return the dictionary containing
        the cdt definition.
        use parse2pycode to get a more usefull python code.
        """
        self.parse()
        return self.commands

    def parse2pycode(self, className=None, classComment=None,
                     derived=vltModulePref+"Process"):
        """
        parse the file and return a python code containing the class
        definition.
        equivalent of:
        f.parse()
        f.pycode(**kwargs)

        Keywords
        --------
        className : (str) the class name. Default, is the Cdt file name
                          if it does not have invlid python characters
        classComment : (str) doc of the class. Default is a explantion
                       of how the code as been created and general uses
        derived : (str) the string of the derived class default is vlt.Process
        """

        self.parse()
        return self.pycode(className=className, derived=derived,
                           classComment=classComment)

    def pycode(self, className=None, classComment=None, derived=vltModulePref+"Process"):
        """
        return the python code definition of this file.
        The file MUST have been parsed first.

        Keywords
        --------
        className = (str) the class name. Default, is the Cdt file name
                          if it does not have invlid python characters
        classComment = (str) doc of the class. Default is a explantion
                       of how the code as been created and general uses
        derived = (str) the string of the derived class default is vlt.Process
        """
        if className is None:
            #take the file name (without extention) as default for className
            className = os.path.splitext(os.path.split( self.name)[1])[0]
            if re.search( "[^a-zA-Z0-9_]" , className) or re.search( "[^a-zA-Z_]" , className[0]):
                raise TypeError("Cannot convert filename '%s' to python class name, contains invalid caracheters, please provide a class name"%(className))
        return dict2py(self.commands, className, derived=derived,
                       classComment=classComment, fileName=self.name)

    def write_pyfile(self, filePath=None, className=None,
                     derived=vltModulePref+"Process",
                     classComment=None, overWrite=True):
        """ write the python code of the curent Cdt file.
        The file MUST have been parsed first: f.parse()

        Return
        ------
        The file path

        Keywords
        --------
        filePath = (str) path to the file. Default will be the cdt file
                         name, with the .py extention inside the
                         config["cdtpydir"] directory.
        overWrite = (bool) over write the file if exists. Default is True
        ** + same keywords as for pycode method **

        """
        if filePath is None:
            fileName = os.path.split(self.name)
            fileName = os.path.splitext(fileName)[0]+".py"
            filePath = cdtpydir + "/" + fileName

        if not overWrite and os.path.exists(filePath):
            raise IOError("The file %s already exists" % (filePath))
        g = open(filePath, "w")

        g.write(
                self.pycode(className=className,
                            classComment=classComment,
                            derived=derived
                            )
                )
        g.close()
        return filePath

    def parse2pyfile(self,  filePath=None, className=None,
                     derived=vltModulePref+"Process", classComment=None, overWrite=True):
        """
        parse the file and write the process class definition to
        a python file.
        equivalent to do:
        > f.parse()
        > f.write_pyfile(file_path)

        Keywords
        --------
        filePath = (str) path to the file. Default will be the cdt file
                         name, with the .py extention inside the
                         config["cdtpydir"] directory.
        overWrite = (bool) over write the file if exists. Default is True
        ** + same keywords as for pycode method **

        """
        self.parse()
        return self.write_pyfile(filePath=filePath, className=className,
                                 classComment=classComment, derived=derived
                                 )

    def reset(self):
        pass

    def commentLine(self, line):
        if debug:
            self.debug += [">>> Read a comment line"]
        return self.readline()

    def textLine(self, line, param):
        if debug:
            self.debug += [">>> Read a help text"]
        while True:
            tmpline = self.readline()
            if not len(tmpline):
                if debug:
                    self.debug += [">>> Finished help text because end of file"]
                self.curentCommand[param] = line
                return ''
            stmpline = tmpline.lstrip()

            if len(stmpline) and stmpline[0]=="@":
                if debug:
                    self.debug += [">>> Finished help text because '@' found"]
                self.curentCommand[param] = line
                return self.readline()
            line += tmpline

    def cteLine(self, line):
        self.cte[line.strip()] =  True
        return self.readline()

    def findIncludeFile(self, fl):
        return ospath.find(fl, defaults=cdtconfig)

    def includeLine(self, line):
        inc, ifl = line.split()
        ifl = ifl.strip().strip('"').strip("'")
        fl = self.findIncludeFile(ifl)
        if fl is None:
            raise Exception("coud not fin cdt file '%s'" % (ifl))
        f = Cdt(fl)

        #  make the commands dictionary of f and self the
        #  same. So everything added by f.parse() will be
        #  added in self.commands
        f.commands = self.commands

        #  parse the include file
        f.parse()
        f.close()

        return self.readline()


    def parameterListStart(self, paramkey):
        if debug:
            self.debug +=  [">>> Starting parameter list"]
        self.curentCommand[paramkey] = OrderedDict()
        self.curentParameters = self.curentCommand[paramkey]
        return self.parameterStart(self.readline())
        
    def parameterListEnd(self, line):
        if debug:
            self.debug +=  [">>> ending parameter list"]
        self.curemtParameters = None
        self.curentParameter  = None
        #return self.parse(line)
        return line

    def parameterStart(self, line):
        if debug:
            self.debug +=  [">>> starting parameter"]
        self.curentParameter = {}
        return self.parameterLine(line)

    def parameterLine(self, iline):
        """
        From what I understand each parameters definition
        are separated by an empty line or PAR_NAME, see example:

        TODO: check what define a new parameter definition block
              Empty line or PAR_NAME keyword ?
        Should be PAR_NAME i think

        PARAMETERS=
            PAR_NAME=           type
            PAR_TYPE=           STRING
            PAR_OPTIONAL=       NO
            PAR_MAX_REPETITION= 1

            PAR_NAME=           params
            PAR_TYPE=           STRING
            PAR_OPTIONAL=       YES
            PAR_MAX_REPETITION= 999
        """
        if not len(iline):
            #  the line is empty end the curent
            #  parameter definition
            self.parameterEnd()
            return self.parameterListEnd()

        line = iline.strip()
        #  a line can have space in it, in this case
        #  it is not considered as a end of Parameter definition
        #  not sure about the grammar
        if not len(line) or line[0:2] == "//":
            return self.readline()

        if line[0:4] != "PAR_":
            #  end the previous/current parameter
            self.parameterEnd()
            #  exit from the Parameters definition
            return self.parameterListEnd(iline)

        spline = line.split("=", 1)
        param, value = spline
        param = param.strip()

        if param[0:4] == "PAR_":  #  at this point always true normaly
            param = param[4:None]

        value = value.strip()
        #  value can have trailing comment
        value = value.split("//")[0]

        #  well if we found PAR_NAME and the name is already
        #  defined in curentParameter so we we end the curent
        #  parameter definition and start a fresh new one
        if param == "NAME" and "NAME" in self.curentParameter:
            self.parameterEnd()
            return self.parameterStart(iline)

        self.curentParameter[param] = value
        return self.readline()

    def parameterEnd(self):
        if debug:
            self.debug +=  [">>> ending parameter"]
        if not len(self.curentParameter):
            #return self.parameterStart()
            return None
        if not "NAME" in self.curentParameter:
            raise Exception("No PAR_NAME for one of the parameter")
        pname =  self.curentParameter.pop('NAME')

        self.curentParameters[pname] = self.curentParameter
        self.curentParameter = None
        return None

    def commandStart(self, commandName):
        if debug:
            self.debug +=  [">>> starting command %s "%commandName]

        self.commands[commandName] = {}
        self.curentCommand = self.commands[commandName]
        return self.readline()

    def commandEnd(self):
        self.curentCommand = None
        return self.readline()

    def commandLine(self, line):

        if self.curentParameter is not None:
            #  we are curently inside a parameter list
            #  definition.
            return self.parameterLine(line)

        spline = line.split("=", 1)
        if len(spline) is 1:
            return self.cteLine(line)

        param, value = spline
        param = param.strip()
        value = value.strip()
        value = value.split("//")[0]  # remove comments after value

        if param == "COMMAND":
            return self.commandStart(value)
        if param in  ["PARAMETERS","REPLY_PARAMETERS"]:
            return self.parameterListStart(param)

        if param == "HELP_TEXT":
            return self.textLine(self.readline(), param )

        if debug:
            self.debug += [">>> Set param %s to value %s"%(param, value)]
        self.curentCommand[param] = value

        return self.readline()


def findCdtFile(file_name, path=None, prefix=None, extention=None):
    """
    find the cdt file_name inside the path list.
    by default path list is in config["cdt"]["path"]
    """
    return ospath.find(file_name, path=path, prefix=prefix, 
                     extention=extention, defaults=cdtconfig
                    )

findProcessFile = findCdtFile    

def processClass(processname, path=None, prefix=None, extention=None):
    """
    Return the dynamicaly created python class of a process

    The program look for the file processname.cdt into the list of path
    directories wich can be set by the path= keyword.
    By default config['cdt']['path'] is used
    """
    fileName = findCdtFile(processname, path=path, prefix=prefix, 
                            extention=extention)
    pycode = Cdt(fileName).parse2pycode()

    exec pycode
    # the pycode should contain the variable proc
    # witch is the newly created object
    # and cls for the class 
    return cls


def openProcess(processname, environment="", path=None, prefix=None, 
                            extention=None):
    """
    return processClass(processname, path)()
        
    Prameters
    ---------
    processname: string 
        the process name (without '.cdt' extention)
    environment: string, optional
        The envirnoment name used for the process 

    path: list, optionale
        list of path where to find the '.cdt' files, default is config['cdt']['path']
        
    Example
    -------
      pnoc = openProcess("pnoControl")
      pnoc.setup( function="INS.MODE ENGENIERING DET.DIT 0.01" )
    
    """
    return processClass(processname, path=path, prefix=prefix, 
                        extention=extention)(environment=environment)
                          

_cmd2ClassDef_str = """
{idt}def {name}(self, **kwargs):
{idt}{idt}return self.msgSend('{name}', kwargs)
{idt}{className}_commands[{name}]
"""
def cmd2ClassDef(nm, helpText="", indent=1):
    """
    internal function used ro create dynamicaly class definition
    of VLT msgSend commands.
    Add the definition of function named nm with its optional helptext
    """
    s =  indentStr*(indent)+"def %s(self, **kwargs):\n"%(nm)
    s += '%s"""\n%s\n%s"""\n'%(  indentStr*(indent+1),  helpText, indentStr*(indent+1))
    s += "%sreturn self.msgSend('%s', kwargs)\n\n"%(indentStr*(indent+1), nm);

    #s += "def msg%s(self, **kwargs):\n"%(nm.capitalize())
    #s += '"""\n%s\n"""\n'%command.helpText
    #s+="    return self.cmdMsgSend('%s', kwargs)\n\n";
    return s


def dict2ClassDef(data, indent=1):
    text = ""
    for cmdname, cmd in data.iteritems():
        text += cmd2ClassDef(cmdname.lower(), cmd.get("HELP_TEXT", ""), indent=indent)
    return text


def _wrf(nm, p):
    return  """    "%s"\t:_ic("%s", "%s"),"""%(nm, nm.upper(), p)


_dict2py_str = """
{generalMouleImport}
{vltModuleImport}
{cdtModuleImport}
class {className}({derived}):
{idt}\"\"\"
{classComment}
{idt}\"\"\"
{idt}{vltModuleImport}
{idt}{cdtModuleImport}
{idt}{buffreadModuleImport}

{idt}commands = {dictpycmd}
{idt}msg = "{className}"

{idt}for c in commands: exec("%s = {cdtModulePref}msg_send_decorator('%s',commands)"%(c,c))

cls  = {className}
"""

def dict2py(data, className, derived=vltModulePref+"Process", indent=0,
            classComment=None, fileName=""):
    """
    Transform a cdt definition dictionary (parsed from Cdt class)
    to a string containing the class python code definition
    """
    if classComment is None:
        classComment = """
This is a {className} class vlt.Process automaticaly generated from file
     {fileName}

To get a list of commands:
  proc.getCommandList()
To print a help on a specific command (e.g. setup)
  proc.help("setup")

proc.help() will return help for every commands
""".format(className=className, fileName=fileName)
    dictpycmd = dict2pyCommands(data, indent=indent)
    idt = indentStr * (indent+1)
    return _dict2py_str.format(**dict(globals().items()+locals().items()))

def keyCommandMaker(command):
    command = command.lower()
    if command in ["in", "as", "if", "or", "and", "with", "break", "continue", "for", "while", "class", "def", "print"]:
        return command.capitalize()
    return command

def keyOptionMaker(option):
    return option

def scripOptionMaker(option):
    return "-%s" % option

# CDT type to python type dictionary transformation
typeDict = {
            "INTEGER": "int",
            "STRING": "str",
            "LOGICAL": "bool",
            "REAL": "float"
           }

# CDT type to format dictionary transformation
formatDic = {
    "INTEGER": '"%d"',
    "LOGICAL": vltModulePref+"formatBoolCommand",
    "REAL": '"%f"'
    }

def type2py(cdt_type, name="", cmd=""):
    """
    convert a CDT type to python type string
    """
    cmd = cmd.lower()
    if cmd in typeExeption:
        if name in typeExeption[cmd]:
            return typeExeption[cmd][name]

    if name in typeExeption['']: #general type exception
        return typeExeption[''][name]

    if cdt_type not in typeDict:
        raise Exception("unknown type '%s'" % cdt_type)
    return typeDict[cdt_type]


def type2pyFormat(cdt_type):
    """ convert a cdt_type to a python format string
    """
    return formatDic.get(cdt_type, '"%s"')


def dict2pyCommands(commands, indent=0):
    """ convert a commands dictionary as parsed by Cdt object
    to a python code Command definition.
    """
    return "OrderedDict([\n"+(",\n".join([dict2pyCommand(k, cmd, indent=indent+1) for k,cmd in commands.iteritems()  ] ))+"])"


def dict2pyCommand(command, data, keyMakerFunc=keyCommandMaker, indent=0):
    return '%s("%s"\t,%sCommand("%s",%s,helpText="""%s""", bufferReader=%s.getreader("%s")))'%(
        indentStr*indent, 
        keyMakerFunc(command), vltModulePref, command, 
        dict2pyOptions(data.get("PARAMETERS",{}), cmd=command), 
        data.get("HELP_TEXT", ""), buffreadClassName , command)


def dict2pyOptions(options, indent=0, cmd=""):
    #return [dict2pyOption(k,opt) for k,opt in options.iteritems()  ]
    return indentStr*indent+"OrderedDict(["+(",".join([dict2pyOption(k,opt,cmd=cmd) for k,opt in options.iteritems()  ] ))+"])"


def dict2pyOption(name, option, cmd=""):
    return """("%s",%sParam("%s", %s, %s))""" % (keyOptionMaker(name),vltModulePref,scripOptionMaker(name), type2py(option.get('TYPE',"str"), name, cmd), type2pyFormat(option.get("TYPE",'"%s"')))
