from .functiondict import FunctionDict
from .mainvlt import DEFAULT_TIMEOUT, EmbigousKey


class Device(FunctionDict):
    """ Device object is subclasse from a FunctionDict object with additional
    usefull methods dedicated to the device e.g. move, close, takeExposure,...


    """
    def __init__(self, fdict, statusKeys=None, proc=None):
        FunctionDict.__init__(self, fdict)

        if statusKeys is not None:
            self.statusKeys = statusKeys
        self._check()
        if proc:
            self.proc = proc

    def _check_keys(self, klist):
        """ check a list of keys, they must be in the dictionary and
        they must not be embigous
        """
        for k in klist:
            if k not in self:
                raise KeyError("Device '%s' Nead the key '%s' to work corectly" % (self.__class__.__name__, k))
            try:
                self[k]
            except EmbigousKey:
                raise KeyError("It seems that the needed key '%s' is not unique" % k)

    def _check(self):
        """ Function to check if all the functionality are here
        for a normal behavior.
        """
        pass


def newDevice(name, proc, dictionary, cls=Device):
    new = cls(dictionary)
    new.proc = proc
    new.update(proc.status(function=name))
    return new






