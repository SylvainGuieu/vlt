
def _hdr_start(f, value):
    f.hdr = {}
    f.inhdr = True
def _hdr_stop(f, value):
    f.inhdr = False

class OBD(file):
    dictionary = None # will be set a t __init__
    cases = {"PAF.HDR.START":_hdr_start,
             "PAF.HDR.STOP" :_hdr_stop
             }

    def __init__(self, *args, **kwargs):
        file.__init__(self, *args, **kwargs)
        self.dictionary = ParameterDictionary()
    def parse(self, line=None, count=0):
        if line is None:
            line = self.readline()
        if not len(line):
            return count


        nline = line.strip()
        if not len(nline):
            return self.parse(self.readline(), count=count)
        if nline[0] == "#":
            return self.parse(self.readline(), count=count)

        spline = nline.split(" ", 1)
