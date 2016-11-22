from ..device import Device
class Lamp(Device):
	def _check(self):
       """ the simple Lamp device needs these keys to work
       corectly : "ST"
       """
       self._check_keys(["", "ST"])
       
    def cmd_turnOn(self):
    	return self['ST'].cmd(True, context=self)

    def cmd_turnOff(self):
    	return self['ST'].cmd(False, context=self)	
    
    def turnOn(self, proc=None):
    	return self.getProc(proc).setup(function=self.cmd_turnOn())

    def turnOff(self, proc=None):
    	return self.getProc(proc).setup(function=self.cmd_turnOff())	
    
    def getStatus(self, proc=None):
    	return self[""].status(proc=self.getProc(proc))
	
	    	