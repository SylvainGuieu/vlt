from __future__ import print_function
import time
import sys

ERROR   = 1
WARNING = 2
NOTICE  = 4 # info and notice are aliases
INFO = 4
DATA = 8 

# Buffer size
BUFFER_SIZE = 100 

# default verbose type 
verbose_type = ERROR+WARNING+NOTICE+DATA
# default level of verbose 
verbose_level = 3

##
# convert the message type code to a string 
msgtype2string_lookup = {ERROR:"ERROR", WARNING:"WARNING", NOTICE:"NOTICE", DATA:"DATA"}



##
# Try to colorate the messages 
try:
    import colorama
    import colorama as col
except:
    def colorize(s, color):
        return s
else:
    def colorize(s, color):
        try:
            clr = getattr(colorama.Fore, color.upper())
        except AttributeError:
            raise ValueError("wrong color %r"%color)    
        return clr+s+colorama.Fore.RESET

colorized_msgtype2string_lookup = {
        ERROR  :colorize( "ERROR",   "RED"),
        WARNING:colorize( "WARNING", "MAGENTA"),
        NOTICE :colorize( "NOTICE" , "BLUE"),
        DATA   :colorize( "DATA"   , "BLACK")
    }

    

def toggle_color(flag):
    """ Turn On/Off the message colorization """
    global stdout_msgtype2string_lookup, msgtype2string_lookup , colorized_msgtype2string_lookup
    if flag:
        stdout_msgtype2string_lookup = colorized_msgtype2string_lookup
    else:
        stdout_msgtype2string_lookup = msgtype2string_lookup        
toggle_color(True)



def contexts2str(contexts):
    if contexts:
            return "[%s]"%(" ".join(contexts))
    return ""

class LogFormat(object):
    def __init__(self, fmt="""{context} {msgtype} {date}: {msg}\n""",
                       msgtype="",
                       datefmt="%Y-%m-%dT%H:%M:%S", 
                       contexts2str=contexts2str):

        self.msgtype = msgtype
        self.contexts2str = contexts2str
        self.datefmt = datefmt
        self.fmt = fmt

    def format(self, contexts, clock, msg, level=1, count=0):
        context = self.contexts2str(contexts)
        date    = time.strftime(self.datefmt, clock)
        return self.fmt.format(
                context=context,
                msgtype=self.msgtype,
                level=level,                                        
                date=date,
                msg =msg, 
                count=count
        )

        

      
class LogOutput(object):
    def __init__(self, wf, msgtypes=None, maxlevel=None, label="", formatlookup=None, colorized=None):
        
        if colorized:
            msgtype2string = lambda tpe: colorized_msgtype2string_lookup.get(tpe,"")
        else:                  
            msgtype2string = lambda tpe: msgtype2string_lookup.get(tpe,"") 
        self.file = None
        
        if isinstance(wf, basestring):
            wf = open(wf, "w")

        if isinstance(wf, file):
            if (wf is sys.stdout):
                if colorized is None:
                    msgtype2string = lambda tpe: colorized_msgtype2string_lookup.get(tpe,"")
                wf = wf.write
                label = label or "stdout"
            elif (wf is sys.stderr):
                if colorized is None:
                    msgtype2string = lambda tpe: colorized_msgtype2string_lookup.get(tpe,"")
                wf = wf.write
                label = label or "stderr"
            else:
                self.file = wf
                label = label or wf.name
                wf = wf.write
                

        elif not hasattr(wf, "__call__"):
            raise ValueError("Output should be a string, a file or a callable object")                    
        self.wf = wf
        self.label = label
        self.msgtypes = msgtypes
        self.maxlevel = maxlevel
        self.formatlookup = formatlookup or {}
        self.msgtype2string = msgtype2string

    def close(self):
        """ if output is a file, close it and return True else return False """    
        file = self.file
        if not file:
            return False
        if (file is sys.stdout) or (file is sys.stderr): 
            return False
        self.file.close()
        return True

    def get_format(self, parent, msgtype):
        try: 
            fmt = self.formatlookup[msgtype]
        except KeyError:
            fmt = parent.formatlookup.get(msgtype, parent.default_format)
        return fmt
        
    def log(self, parent, msg, clock, level=1, msgtype=NOTICE):       
        msgtypes = parent.msgtypes if self.msgtypes is None else self.msgtypes
        ## if msgtype is not in msgtypes, return 
        if not msgtypes & msgtype:
            return 0
        maxlevel = parent.maxlevel if self.maxlevel is None else self.maxlevel
        ## do not do anything if level is too hight            
        if level>maxlevel: 
            return 0

        fmt = self.get_format(parent, msgtype)
        formated_msg = fmt.format(
                                context=parent.logcontext(),
                                msgtype=self.msgtype2string(msgtype),
                                msglevel=level,                                        
                                date=time.strftime(parent.date_format, clock),
                                msg =msg, 
                                count=parent.count
                            )
        self.wf(formated_msg)
        return 1
            



class Log(object):
    """A Log set of function for Gravity """
    default_format = """{context} {msgtype} {date}: {msg}\n"""         
    formatlookup = {DATA:"{msg}"}
    date_format = "%Y-%m-%dT%H:%M:%S"

    msgtypes  = verbose_type
    maxlevel  = verbose_level
    context = None

    BUFFER_SIZE = BUFFER_SIZE

    #########################################################
    #
    buffer  = {}   

    
    
    def search_buffer(self, context=None, msgtype=None, level=None, msg=None):
        buffer = self.buffer
        CONTEXT, MSGTYPE, LEVEL, TIME, MSG = range(5)

        found = []
        for info in buffer:
            if context:
                if info[CONTEXT][0:len(context)] != context:
                    continue
            if msgtype and info[MSGTYPE]!=msgtype:
                continue
            if level is not None and info[LEVEL]>level:
                continue
            if msg and not msg in info[MSG]:
                continue
            found.append(info)
        return found                      
            
    

    def clear_buffer(self):
        buffer = self.buffer
        while buffer:
            buffer.pop()        

    def add_to_buffer(self, context, tpe, level, time, msg):
        """ and a message of some contexts and message type to the buffer 

        several instances can share the same buffer        
        """

        buffer = self.buffer
        buffer.append((context, tpe, level, time, msg))
        while len(buffer)>BUFFER_SIZE:
            buffer.pop(0)


    def __init__(self, outputs=None, msgtypes=None, maxlevel=None, context=None, contexts=None, buffer=None):
        """ create a log writing object.


        A log object is defined by 
         -outputs (can be stdout a file, ...) 
         -msgtypes allowed message type for each outputs: ERROR, WARNING, NOTICE or DATA
                  or combination of all
         -maxlevel a maximum level for each output all call with a higher level will be ignored  
         -contexts : list of string that set the log context
         -default_format :  a default format for all msgtype 
         -formatlookup : a dictionary of format for each types.
                the format accept the following keys:
                    context, msgtype, msglevel, date, count, msg
                the date format can be defined with the date_format attribute    
                              
        Parameters
        ----------
        outputs : list, optional
            a list of : string -> path to a file, will be opened in "w" mode 
                        file   -> f.write is used to output the message
                        callable object -> with a signnature func(msg) where msg is a string
                        tuple -> if a tuple must be (f, msgtypes) or (f, msgtypes, maxlevel)
            
                                where f can be a file or a string.
                                This way one can set a different maxlevel and msgtype 
                                for each output
                                maxlevel and msgtype can be omited or None to set to their 
                                default value                                    
            e.g. :
                log = Log(outputs=[(sys.stdout, NOTICE+DATA), (sys.stderr, ERROR)])                               
            If no output is given the default is stdout.
            
        msgtypes : int(binary) or string optional 
            default msgtypes for each outputs if not defined.
            each msgtypes bits turn on/off the allowed msgtype.
            One can use the sum combination of the defined constants ERROR, WARNING, NOTICE and DATA
            
            The bytes are as follow:
                #byte  int  msgtype 
                1      1    ERROR 
                2      2    WARNING
                3      4    NOTICE
                4      8    DATA  

            e.g. :   msgtypes = ERROR+WARNING  -> will print only the error and warning messages   

            Also msgtypes can be astring containing a combination of the caracters  'E','W','N' or 'D'
             msgtypes = ERROR+WARNING+NOTICE equivalent to msgtypes = "EWN" 
    
        maxlevel : int, optional
            The default maxlevel for each output if not defined.    
            If not given maxlevel=1 

        context : string, optional
            the context is added to the list of `contexts`
        
        contexts : iterable
            list of string contest

        """

        if maxlevel is not None:
            self.maxlevel = maxlevel
        if msgtypes is not None:
            if isinstance(msgtypes, basestring):
                msgtypes = sum( (s in msgtypes)*bit for s,bit in [('E',ERROR),('W',WARNING),('N',NOTICE),('D',DATA)] )
            self.msgtypes   = msgtypes


        if contexts is None:
            self.contexts = tuple()
        else:
            self.contexts = tuple(contexts)                

        if context:
           self.contexts += (context,)         
               

        self.outputs = []                       
        if outputs is None:
            self.add_output(sys.stdout, None, None)
        else:
            for output in outputs:
                if isinstance(output, LogOutput):
                    self.outputs.append(output)
                else:    
                    output = output if isinstance(output, tuple) else (output,)       
                    self.add_output(*output)

        # make a copy of the class default        
        self.formatlookup = dict(self.formatlookup)        
        self.count = 0

        if buffer is not None:
            self.buffer = buffer
        else:
            self.buffer = []
                                
        self.enable()            


    def add_contexts(self, *contexts):
        """ pill up new contexts to the log """
        self.contexts = self.contexts+contexts

    def remove_contexts(self, *contexts):
        """ remove the given contexts from the context list """
        newcontexts = list(self.contexts)
        for context in contexts:        
            try:
                newcontexts.remove(context)
            except ValueError:
                pass
        self.contexts = tuple(newcontexts)            

    def new(self, outputs=None, msgtypes=None, maxlevel=None, context=None, contexts=None, buffer=None):
        new = self.__class__(
            self.outputs if outputs is None else outputs,
            self.msgtypes if msgtypes is None else msgtypes,
            self.maxlevel if maxlevel is None else maxlevel,
            context = context,
            contexts = self.contexts if contexts is None else contexts,
            buffer = self.buffer if buffer is None else buffer
        )
        return new


    def logcontext(self):
        if self.contexts:
            return "[%s]"%(self.contexts)
        return ""        

    def add_output(self, wf,  msgtypes=None, maxlevel=None, label="", formatlookup=None, colorized=None):
        """ Add a new output to the log 

        Parameters
        ----------
        output : 
            string -> path to a file, will be opened in "w" mode 
            file   -> f.write is used to output the message
            callable object -> with a signnature func(msg) where msg is a string
        msgtype : int, optional
            the message type bit value for this output
            One can use the sum combination of the defined constants ERROR, WARNING, NOTICE and DATA            
            The bytes are as follow:
                #byte  int  msgtype 
                1      1    ERROR 
                2      2    WARNING
                3      4    NOTICE
                4      8    DATA 
            If not given the default of the log is taken                  
        maxlevel : int
            The maximum level of message for this output            
            If not given take the log default            
        
        Example
        -------
            log = Log(msgtype=WARNING+ERROR) # by default log as only one output : sys.stdout
            log.add_output(sys.stderr, msgtype=ERROR)
                                                            
        """
        self.outputs.append(LogOutput(wf, msgtypes, maxlevel, 
                                        label=label, 
                                        formatlookup=formatlookup, 
                                        colorized=colorized
                                    )
            )        

    def close(self):
        """ Attempt to close all the files open as output 
        
            The log will still work with other output (e.g. stdout)
        """        
        for output in self.outputs:
            if output.close():
                self.outputs.remove(output)

    def disable(self):
        """ put the log quiet 
        
        use log.enable() to put it back
        """
        self._disabled = True

    def enable(self):
        """ send back the log to normal behavior """    
        self._disabled = False

    def log(self, msg, level=1, msgtype=NOTICE):
        if self._disabled:
            return
        clock = time.gmtime()
        cte = 0
        for output in self.outputs:
            cte += output.log(self, msg, clock, level, msgtype)    
        
        if cte: # add to buffer only if it has been added to some outputs            
            self.add_to_buffer(self.contexts, msgtype, level, clock, msg)
            self.count += 1

    def set_format(self, msgtype, fmt):
        if msgtype == 0:
            self.default_format = fmt
        self.formatlookup[msgtype] = fmt        

    def data(self, msg, level=1):
        """ log message as DATA """
        self.log(msg, level, DATA)

    def set_data_format(self,fmt):
        """ set the format for DATA messages """
        self.set_format(DATA, fmt)    

    def info(self, msg, level=1):
        """ log message as INFO=NOTICE """
        self.log(msg, level, NOTICE)

    def set_info_format(self, fmt):
        """ set the format for INFO messages """
        self.set_format(INFO, fmt)

    def notice(self, msg, level=1):
        """ log message as NOTICE=INFO """
        self.log(msg, level, NOTICE)

    def set_notice_format(self, fmt):
        """ set the format for NOTICE messages """
        self.set_format(NOTICE, fmt)

    def warning(self, msg, level=1):
        """ log message as WARNING """
        self.log(msg, level, WARNING)

    def set_warning_format(self, fmt):
        """ set the format for WARNING messages """
        self.set_format(WARNING, fmt)

    def error(self, msg, level=1):
        """ log message as ERROR """
        self.log(msg, level, ERROR)	 
    
    def set_error_format(self, fmt):
        """ set the format for ERROR messages """
        self.set_format(ERROR, fmt)              

## open a new log         
log = Log()    
