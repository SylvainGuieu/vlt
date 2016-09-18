
import vlt
import vlt.buffread as buffread

def msgdef(msg,commands):
    def tmp(self,**kwargs):
        return self.msgSend( msg, kwargs)
    tmp.__doc__ = commands[msg].helpText
    return tmp

buffreader = buffread.buffreader
osbControl_commands = {
    "cont"	:vlt.Command("CONT",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"at":vlt.Param("-at", str, "%s")},helpText="""Continue a paused exposure at a given optional time. The following options are
supported:
    at <time>                specify the time when the exposure must be resumed
                            (default is now). The time format is (ISO8601):
                            [[CC]YY[-]MM[-]DD[T| ]]HH[:]MM[[:]SS[.TTT]]
    expoId <expoId>         integer number specifying exposure number (optional)
""", bufferReader=buffreader.getreader("CONT")),
    "addfits"	:vlt.Command("ADDFITS",{"info":vlt.Param("-info", str, "%s"),"expoId":vlt.Param("-expoId", int, "%d"),"extname":vlt.Param("-extname", str, "%s"),"detId":vlt.Param("-detId", str, "%s"),"extnum":vlt.Param("-extnum", int, "%d")},helpText="""Add information to the FITS header of an acquisition frame. The following
options are supported:
    expoId <expoId>         integer number specifying exposure number (optional)
    info <keyword1> <value1> [<keyword2> <value2> ...]
                            specify one or more parameters with the associated
                            value which have to be added to FITS header. With:
                                    keywordX: a short-FITS keyword
                                    valueX:   the value for the keyword
    extnum                  Serial number of the extention (1..n)
                            If parameter is omitted the kw is stored in 
                            the primary header (optional)
    extname                 Name of extention where the keywords (specified via -info)	
                            should be stored. Both parameters -extnum or -extname 
                            are optional but only one of them should be present.
""", bufferReader=buffreader.getreader("ADDFITS")),
    "standby"	:vlt.Command("STANDBY",{"subSystem":vlt.Param("-subSystem", str, "%s")},helpText="""Switches the local server and its associated subsystems or only the specified
subsystem to the STANDBY state. The following option is 
supported:
    subSystem <subSystem>   name of the subsystem to switch to STANDBY state.
""", bufferReader=buffreader.getreader("STANDBY")),
    "stopopt"	:vlt.Command("STOPOPT",{},helpText="""Abort on-going flux optimazation
""", bufferReader=buffreader.getreader("STOPOPT")),
    "setup"	:vlt.Command("SETUP",{"function":vlt.Param("-function", vlt.dtypeFunctionList, "%s"),"noMove":vlt.Param("-noMove", bool, vlt.formatBoolCommand),"expoId":vlt.Param("-expoId", int, "%d"),"noExposure":vlt.Param("-noExposure", bool, vlt.formatBoolCommand),"file":vlt.Param("-file", str, "%s"),"check":vlt.Param("-check", bool, vlt.formatBoolCommand)},helpText="""Set-up functions, as part of the preparation of an exposure. The following
options are supported:
    expoId <expoId>	A unique id of an exposure. The expoId should be set
			to 0 in order to setup a new exposure. The  successful 
			command returns a new valid expoId (increasing by 1 
			the last expoId), which is always greater then 0. Any 
			consequent setup and commands belonging to this 
			exposure must use this expoId.
    file <file1> [<file2>]  
			specify one or more set-up files
    function <keyword1> <value1> [<keyword2> <value2> ...]
          		specify one or more parameters with the associated
                        value. keywordN: a short-FITS keyword
			valueN:   the value for the keyword
			First setup must contain the instrument mode (INS.MODE).
			An image taking exposure should setup the imagefilename
			(OCS.DET.IMGNAME) befor the exposure can be started. 
    noMove		indicate that the functions contained in the setup
			files and/or list of parameters are not moved, but
      			otherwise the values get the full setup treatment.
    check      		indicate that list of parameters is checked for
    			semantic validity, without storing values or moving
                        functions.
    noExposure   	In special cases the SETUP may not correspond to any 
			exposures (e.g. there is no detector connected to 
			the OS). In this case the parameter noExposure is 
			applicable. Use with caution, and do not use together 
			with parameter expoId. Command returns: -1 
			(invalid expoId). 
""", bufferReader=buffreader.getreader("SETUP")),
    "debug"	:vlt.Command("DEBUG",{"action":vlt.Param("-action", int, "%d"),"log":vlt.Param("-log", int, "%d"),"timer":vlt.Param("-timer", int, "%d"),"verbose":vlt.Param("-verbose", int, "%d")},helpText="""Changes logging levels on-line. Levels are defined from 1 to 5 whereby
level 1 produces only limited number of logs, and level 5 produces logs
at a very detailed level. The following options are supported:
    log <level>     level for standards logs which are stored into the
                    standard VLT log file.
    verbose <level> level for logs that are written to stdout.
    action <level>  level for action logs which are written into a DB 
                    attribute.
    timer <level>   level for timer logs which are used to report the 
                    time for performing a given action. This information
                    is stored into the standard VLT log file and written 
                    to stdout, according to the level of these logs. 
""", bufferReader=buffreader.getreader("DEBUG")),
    "off"	:vlt.Command("OFF",{"subSystem":vlt.Param("-subSystem", str, "%s")},helpText="""Switches the local server and its associated subsystems or only the specified
subsystem to the OFF state. The following option is supported:
    subSystem <subSystem>   name of the subsystem to switch to the OFF state.
""", bufferReader=buffreader.getreader("OFF")),
    "optflux"	:vlt.Command("OPTFLUX",{"gridGeom":vlt.Param("-gridGeom", str, "%s"),"beam":vlt.Param("-beam", int, "%d"),"save":vlt.Param("-save", str, "%s"),"gridStep":vlt.Param("-gridStep", float, "%f"),"nDit":vlt.Param("-nDit", int, "%d")},helpText="""Perform flux optimazation
""", bufferReader=buffreader.getreader("OPTFLUX")),
    "comment"	:vlt.Command("COMMENT",{"expoId":vlt.Param("-expoId", int, "%d"),"clear":vlt.Param("-clear", bool, vlt.formatBoolCommand),"detId":vlt.Param("-detId", str, "%s"),"string":vlt.Param("-string", str, "%s")},helpText="""Add a comment to the FITS header of an exposure. The following options are
supported:
    expoId <expoId>         integer number specifying exposure number (optional)
    comment <comment>       comment string to be added to the FITS header.
    clear                   if 'true' the list of comments already added will
                            first be cleared.
""", bufferReader=buffreader.getreader("COMMENT")),
    "gethdr"	:vlt.Command("GETHDR",{"expoId":vlt.Param("-expoId", int, "%d"),"btblFileName":vlt.Param("-btblFileName", str, "%s"),"detId":vlt.Param("-detId", str, "%s"),"hdrFileName":vlt.Param("-hdrFileName", str, "%s")},helpText="""Internal command. Creates a header file.
""", bufferReader=buffreader.getreader("GETHDR")),
    "expstrt"	:vlt.Command("EXPSTRT",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s")},helpText="""Internal SOS-OS command.  SOS sends this command to the OS-es which 
are on the subsystemlist but not started.
When OS receives this command it calles the startpreproc function.
""", bufferReader=buffreader.getreader("EXPSTRT")),
    "online"	:vlt.Command("ONLINE",{"subSystem":vlt.Param("-subSystem", str, "%s")},helpText="""Switches the local server and its associated subsystems or only the specified
subsystem from STANDBY state to the ON-LINE state. The following option is 
supported:
    subSystem <subSystem>   name of the subsystem to switch from STANDBY state
                            to the ON-LINE state.
""", bufferReader=buffreader.getreader("ONLINE")),
    "status"	:vlt.Command("STATUS",{"function":vlt.Param("-function", vlt.dtypeFunctionList, "%s"),"expoId":vlt.Param("-expoId", int, "%d")},helpText="""Get the status of the functions in the list of arguments (default: get the
status of all functions). The following options are supported:
    expoId <expoId>         integer number specifying exposure number (optional)
    function [<keyword1> <keyword2> ...]
                            specify any detector, instrument or telescope
                            function.

The reply buffer has the format:
     "<no of keys>,<key 1> <value 1>,<key 2> <value 2>,..."
""", bufferReader=buffreader.getreader("STATUS")),
    "pause"	:vlt.Command("PAUSE",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"at":vlt.Param("-at", str, "%s")},helpText="""Pause the current exposure at a given optional time. The following options are
supported:
    at <time>               specify the time when the exposure has to be paused
                            (default is now). The time format is (ISO8601):
                            [[CC]YY[-]MM[-]DD[T| ]]HH[:]MM[[:]SS[.TTT]]
    expoId <expoId>         integer number specifying exposure number (optional)
""", bufferReader=buffreader.getreader("PAUSE")),
    "end"	:vlt.Command("END",{"expoId":vlt.Param("-expoId", int, "%d"),"all":vlt.Param("-all", bool, vlt.formatBoolCommand),"detId":vlt.Param("-detId", str, "%s")},helpText="""End the current exposure as soon as possible and read out the data. The
following options are supported:
    expoId <expoId>         integer number specifying exposure number (optional)
    detId                   ends the exposure specified on the given detector 
    all                     ends all running exposures and  cancells exposures 
                            that has not yet been started
""", bufferReader=buffreader.getreader("END")),
    "measure"	:vlt.Command("MEASURE",{"params":vlt.Param("-params", vlt.dtypeFunctionList, "%s"),"type":vlt.Param("-type", str, "%s")},helpText="""Performs measurement. The following options are supported:
    type <measType>         specify the type of measurement  to be performed.
    params <param1> <value1> [<param2> <value2> ...]
                            specify one or more parameters with the associated
                            value. With:
                                    paramX: a short-FITS keyword
                                    valueX: the value for the keyword
""", bufferReader=buffreader.getreader("MEASURE")),
    "start"	:vlt.Command("START",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"at":vlt.Param("-at", str, "%s")},helpText="""Start an exposure at a given optional time. The following options are supported:
    expoId <expoId>         integer number specifying exposure number (optional)
    at <time>               specify the time when the exposure must be started
                            (default is now). The time format is (ISO8601):
                            [[CC]YY[-]MM[-]DD[T| ]]HH[:]MM[[:]SS[.TTT]]
""", bufferReader=buffreader.getreader("START")),
    "state"	:vlt.Command("STATE",{"subSystem":vlt.Param("-subSystem", str, "%s")},helpText="""Returns the current state and sub-state of the server or of the specified
subsystem. The format of the returned string is STATE/SUBSTATE, e.g.
ONLINE/IDLE. The following options are supported:
    subSystem <subSystem>   specify the name of the sub-system for which
                            the state or sub-state has to be returned 

The standard states of a server are:
    OFF:     the software is loaded, but it is not operational.

    STANDBY: the software is loaded and initialised, the hardware is software
             initialised, but in standby (applicable parts switched off, 
             brakes clamped, etc.)

    ONLINE:  the software is loaded and initialised, the hardware is hardware
             initialised and fully operational.
""", bufferReader=buffreader.getreader("STATE")),
    "version"	:vlt.Command("VERSION",{},helpText="""Returns the version of the software.
""", bufferReader=buffreader.getreader("VERSION")),
    "clean"	:vlt.Command("CLEAN",{},helpText="""Internal command. Clears the OS exposure table and sets the expoId 
to zero, i.e  to the initial value.
""", bufferReader=buffreader.getreader("CLEAN")),
    "forward"	:vlt.Command("FORWARD",{"subSystem":vlt.Param("-subSystem", str, "%s"),"command":vlt.Param("-command", str, "%s"),"arguments":vlt.Param("-arguments", str, "%s")},helpText="""This command is forwards the specified commands with a specified arguments 
to the specified sub-system. 
FORWARD returns the reply of the sub-system command as a
string.The following option is supported:
    subSystem <subSystem>   name of the subsystem to which the command has to
                            be forwarded.
    command <command>       name of the command.
    arguments <params>      optional command parameters.
""", bufferReader=buffreader.getreader("FORWARD")),
    "wait"	:vlt.Command("WAIT",{"all":vlt.Param("-all", bool, vlt.formatBoolCommand),"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"header":vlt.Param("-header", bool, vlt.formatBoolCommand),"cond":vlt.Param("-cond", str, "%s"),"mode":vlt.Param("-mode", str, "%s"),"detlist":vlt.Param("-detlist", str, "%s"),"first":vlt.Param("-first", bool, vlt.formatBoolCommand)},helpText="""Wait for exposure completion and return the exposure status. 
The following parameters are supported:
    expoId <expoId>     integer number specifying exposure number (optional); 
			The expoId must be in correspondace with the expoid 
			returned by the first SETUP command of the 
			belonging exposure. The exoposure with the same expoId 
			has to be started via START command before WAIT command
			is sent. If expoId is omitted, the command refers to 
			the last started exposure.
    detId  <detname>    string specifying the the detector	
    first               This parameter is useful for optimising the execution 
			of parallel exposures. It can be run in two ways  
			(depending on the setting of parameter mode ):
                       	CurrRunning (default): 
				Waits until one of the currently running 
				exposures is completed/failed/aborted.
				Returns the name of the detector. 
                        detlist: Carries out an initial check to see if any of 
				the detectors (given by parameter 'detlist') 
				has already reached the given condition 
				(finished as default).
			Should not be used together with parameter 'detId'.
                        
    all                 Wait untill all the exposures has been succesfully 
			finished or reached the specificed condition.
    cond                Condition of exposure to be reached before the last 
			reply sent. Typically used for optimised exposure 
			sequence. The following conditions can be set: 
			ObsEnd; CanSetupNextObs; CanStartNextObs
			ObsEnd (default): Condition denoting that the exposure 
				is completed and the image file has been merged
				 with headers and archived.
			CanSetupNextObs: Condition when new exposure can be 
				setup without interrupting the currently 
				running exposure. For NGCOPT it means reaching 
				the status READING_OUT. For NGCIR detector it 
				means reaching the status TRANSFERRING. Please 
				see also configuration OCS.DETi.OPTSEQ to alter
				the behaviour. 
			CanStartNextObs: Condition when next exposure can be 
				started. I.e. the currently running observation
				has been successfully finished, headers from 
				other subsystems has been collected and merging
				process has been informed to archive the image.
    header              (obsolate) equivalent to '-cond CanStartNextObs'. Kept 
			for backcompatibility.  
    mode                only together with 'first' see description at first
    detlist             only together with 'first' see description at first
For more details see BOSS usermanual:  VLT-MAN-ESO-17240-2265 
""", bufferReader=buffreader.getreader("WAIT")),
    "expend"	:vlt.Command("EXPEND",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"path":vlt.Param("-path", str, "%s")},helpText="""Internal SOS-OS command.  SOS sends this command to its OS and ICS subsystems.
When OS receives this command it forwards it to its ICS subsystems.
""", bufferReader=buffreader.getreader("EXPEND")),
    "ping"	:vlt.Command("PING",{},helpText="""Returns a reply.
Used to check if the process is alive.
""", bufferReader=buffreader.getreader("PING")),
    "access"	:vlt.Command("ACCESS",{"subSystem":vlt.Param("-subSystem", str, "%s"),"info":vlt.Param("-info", bool, vlt.formatBoolCommand),"mode":vlt.Param("-mode", str, "%s")},helpText="""Changes the ACCESS mode of the subsystems.
    subSystem <subSystem>   Name of the subsystem the access mode of which 
                            is to be changed. Name should be given according to  
                            the configuration file. 
                            When set to 'ALL' the mode of all subsystems is changed. 
                           	                          	
    mode <mode>             Value can be set to IGNORE or NORMAL.
	                    If subsystem mode set to IGNORED, all commands that are sent to 
                            this are ignored.
  
    info                    returns the ACCESS mode of all subsystems
""", bufferReader=buffreader.getreader("ACCESS")),
    "abort"	:vlt.Command("ABORT",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s")},helpText="""Abort the current exposure immediately. Image data are lost. The following
options are supported:
    expoId <expoId>         integer number specifying exposure number (optional)
""", bufferReader=buffreader.getreader("ABORT")),
    "exit"	:vlt.Command("EXIT",{},helpText="""Terminates the process.
""", bufferReader=buffreader.getreader("EXIT")),
    "config"	:vlt.Command("CONFIG",{},helpText="""Read again the configuration files of the instrument.
""", bufferReader=buffreader.getreader("CONFIG"))}


class osbControl(vlt.Process):
    """

This is a osbControl class vlt.Process automaticaly generated from file 
     /Users/guieu/python/Catalog/vlt/CDT/osbControl.cdt

To get a list of commands:
  proc.getCommandList()      
To print a help on a specific command (e.g. setup)
  proc.help("setup")
  
proc.help() will return a complete help

    """
    commands = osbControl_commands
    for c in osbControl_commands: exec("%s = msgdef('%s',osbControl_commands)"%(c,c))

proc = osbControl("osbControl")
