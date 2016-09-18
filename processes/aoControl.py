
import vlt
import vlt.buffread as buffread

def msgdef(msg,commands):
    def tmp_call(self, function=""):
        return self.msgSend( msg, {"function":function})
    tmp_call.__doc__ = formhelp(msg,commands[msg])
    return tmp_call
def formhelp(msg,command):
    return msg+"("+" ,".join(k+"=%s"%o.dtype for k,o in command.options.iteritems())+")\n\n"+command.helpText
buffreader = buffread.buffreader



ao_commands = {
    "setup"	:vlt.Command("SETUP",
                             {"function":vlt.Param("", vlt.dtypeFunctionList, "%s")},
helpText="""Set-up functions to the dm 
options are supported:
    <keyword1> <value1> [<keyword2> <value2> ...]
          		specify one or more parameters with the associated
                        value. keywordN: a short-FITS keyword
			valueN:   the value for the keyword
			First setup must contain the instrument mode (INS.MODE).
			An image taking exposure should setup the imagefilename
			(OCS.DET.IMGNAME) befor the exposure can be started. 

""", bufferReader=buffreader.getreader("SETUP")), 
    "status"	:vlt.Command("STATUS",{"function":vlt.Param("", vlt.dtypeFunctionListMsg, "%s")},helpText="""Get the status of the functions in the list of arguments (default: get the
status of all functions). The following options are supported:
                    [<keyword1> <keyword2> ...]
The reply buffer has the format:
     "<no of keys>,<key 1> <value 1>,<key 2> <value 2>,..."
""", bufferReader=buffreader.getreader("status2"))
}

#####################
##  PATCH 
##
#####################
class SendCommandSSh(vlt.SendCommand):
    ssh_connect = "user@host"
    def cmdMsgSend(self, command, options=None):
        options = options or {}
        return ("""ssh %s %s %s"""%(self.ssh_connect, self.msg_cmd, self.cmd(command,options))).replace('"', '\\"')

import os
if  os.getenv("HOST") == "wbeti":
    class aoControl(SendCommandSSh):
        ssh_connect = "betimgr@wbeaos"
        commands = ao_commands        
else:
    class aoControl(vlt.SendCommand):
        commands = ao_commands
    #for c in ao_commands: exec("%s = msgdef('%s',ao_commands)"%(c,c))





for c in ao_commands:
    setattr( aoControl, c,  msgdef(c,ao_commands))
