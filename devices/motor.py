from ..device import Device
class Motor(Device):
    """ Motor is a device with the following additional methods

    moveTo : move to one position
    moveBy : move by a relative number of encrel

    and their coresponding cmd method cmdMoveTo, cmdMoveBy, ...
    """
    def _check(self):
       """ the simple motor device needs these keys to work
       corectly : "NAME", "ENC", "ENCREL", "INIT", "STOP"
       """
       self._check_keys(["NAME", "ENC", "ENCREL", "INIT", "STOP"])


    def cmd_moveTo(self,targetpos):
        if issubclass(type(targetpos), str):
            return self['NAME'].cmd(targetpos, context=self)
        return self['ENC'].cmd(targetpos, context=self)

    def cmd_moveBy(self,encrel):
        return self['ENCREL'].cmd(encrel, context=self)

    def moveTo(self, targetpos, proc=None):
        return self.getProc(proc).setup(function=self.cmd_moveTo(targetpos))

    def moveBy(self,encrel, proc=None):
        return self.getProc(proc).setup(function=self.cmd_moveBy(encrel))
