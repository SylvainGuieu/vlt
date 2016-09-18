
import vlt
import vlt.buffread as buffread

def msgdef(msg,commands):
    def tmp(self,**kwargs):
        return self.msgSend( msg, kwargs)
    tmp.__doc__ = formhelp(msg,commands[msg])
    return tmp
def formhelp(msg,command):
    return msg+"("+" ,".join(k+"=%s"%o.dtype for k,o in command.options.iteritems())+")\n\n"+command.helpText

buffreader = buffread.buffreader
rtdc_commands = {
    "ping"	:vlt.Command("PING",{},helpText="""Ping process.
""", bufferReader=buffreader.getreader("PING")),
    "script"	:vlt.Command("SCRIPT",{"script":vlt.Param("-script", str, "%s")},helpText="""Execute a tcl procedure (script) defined in rtdc.
""", bufferReader=buffreader.getreader("SCRIPT"))}


class rtdc(vlt.Process):
    """

This is a rtdc class vlt.Process automaticaly generated from file 
     /Users/guieu/python/Catalog/vlt/CDT/rtdc.cdt

To get a list of commands:
  proc.getCommandList()      
To print a help on a specific command (e.g. setup)
  proc.help("setup")
  
proc.help() will return a complete help

    """
    commands = rtdc_commands
    for c in rtdc_commands: exec("%s = msgdef('%s',rtdc_commands)"%(c,c))

proc = rtdc("rtdc")
