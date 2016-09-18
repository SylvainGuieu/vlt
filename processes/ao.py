
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



ao_commands = {
    "setup"	:vlt.Command("SETUP",
                             {"":vlt.Param("", vlt.dtypeFunctionList, "%s")},
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
    
}
class aoControl(vlt.Process):
    commands = ao_commands
    for c in ao_commands: exec("%s = msgdef('%s',pnoControl_commands)"%(c,c))
