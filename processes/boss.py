
import vlt
import vlt.buffread as buffread

def msgdef(msg,commands):
    def tmp(self,**kwargs):
        return self.msgSend( msg, kwargs)
    tmp.__doc__ = commands[msg].helpText
    return tmp

buffreader = buffread.buffreader
boss_commands = {
    "expend"	:vlt.Command("EXPEND",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s"),"path":vlt.Param("-path", str, "%s")},helpText="""Internal SOS-OS command.  SOS sends this command to its OS and ICS subsystems.
When OS receives this command it forwards it to its ICS subsystems.
""", bufferReader=buffreader.getreader("EXPEND")),
    "gethdr"	:vlt.Command("GETHDR",{"expoId":vlt.Param("-expoId", int, "%d"),"btblFileName":vlt.Param("-btblFileName", str, "%s"),"detId":vlt.Param("-detId", str, "%s"),"hdrFileName":vlt.Param("-hdrFileName", str, "%s")},helpText="""Internal command. Creates a header file.
""", bufferReader=buffreader.getreader("GETHDR")),
    "expstrt"	:vlt.Command("EXPSTRT",{"expoId":vlt.Param("-expoId", int, "%d"),"detId":vlt.Param("-detId", str, "%s")},helpText="""Internal SOS-OS command.  SOS sends this command to the OS-es which 
are on the subsystemlist but not started.
When OS receives this command it calles the startpreproc function.
""", bufferReader=buffreader.getreader("EXPSTRT")),
    "clean"	:vlt.Command("CLEAN",{},helpText="""Internal command. Clears the OS exposure table and sets the expoId 
to zero, i.e  to the initial value.
""", bufferReader=buffreader.getreader("CLEAN"))}


class boss(vlt.Process):
    """

This is a boss class vlt.Process automaticaly generated from file 
     /Users/guieu/python/Catalog/vlt/CDT/boss.cdt

To get a list of commands:
  proc.getCommandList()      
To print a help on a specific command (e.g. setup)
  proc.help("setup")
  
proc.help() will return a complete help

    """
    commands = boss_commands
    for c in boss_commands: exec("%s = msgdef('%s',boss_commands)"%(c,c))

proc = boss("boss")
