import re

class KeywordFile(file):
    in_header = False
    reg = re.compile("""^([^:]*):([^:]*)$""")

    cases = {
        # func of signautre (f, key, value, more)

    }

    # key_case is a dict of dict.
    # Each item is the level of the path to test the keys
    key_cases = {
        # func of signature (f, path, value, more)
        # 0: {"NEW":func}
        # 1: {"NAME": func_for_name"}
    }

    # value cases is a dictionary with a test function as key
    # and a function that return the new value
    # this is helpfull for instance for "ISF INS.DEFAULT" to
    # return the value of INS.DEFAULT in ISF
    value_cases = {
    # test func siganture is (value)
    # called func signature is (f, value) and should return a new value
    }
    comment_char = "#"
    cdict = "parameters"
    def __init__(self, *args, **kwargs):
        file.__init__(self, *args, **kwargs)
        self.parameters = {}
        self.header = {}

    def say(self, txt):
        print txt

    def start_header(self):
        self.in_header = True
        self.cdict = "header"

    def end_header(self):
        self.in_header = False
        self.cdict = "parameters"

    def match_line(self, line):
        """match line should return a tuple of 3 string
        key, value, more
        more is eventual things left on line, for instance, if line is:
        KEY1 "VAL1" ; KEY2 "VAL2"
        and ';' act as a new line, more will be: KEY2 "VAL2"
        """
        m = self.reg.match(line.strip())
        if not m:
            return None, None, None

        groups = m.groups()
        return groups[0], groups[1], ""

    def get(self, path, default=None):
        d = self.dictionary
        for item  in path:
            if not item in d:
                return default
            d = d[item]
        return d

    def set(self, path, value):
        d = self.dictionary
        last = path[-1]
        if not isinstance(last, basestring):
            # the last element is suposed to be a function
            # of signature (previous_value, new_value)
            # e.g : lambda p,n: p+n
            if len(path)<2:
                raise Exception("If last path is not string path must have a len of at least 2 got %s" % path)
            for item in path[:-2]:
                if not item in d:
                    d[item] = {}
                d = d[item]
            item = path[-2]

            d[item] = last(d[item],value)
        else:
            for item in path[:-1]:
                if not item in d:
                    d[item] = {}
                d = d[item]

            last = path[-1]
            d[path[-1]] = value

    def key2path(self, key):
        return [key]

    def get_cdict(self):
        return getattr(self, self.cdict)
    dictionary = property(fget=get_cdict)


    def parse(self):
        self.line = self.readline()
        while len(self.line):
            self.parse_line(self.line)
            self.line = self.readline()
        self.end()
                    
    def end(self):
        pass        

    def parse_line(self, line):
        if line is None or not len(line):
            return
        if self.comment_char and line[0] == self.comment_char:
            return

        key, value, more = self.match_line(line)
        if more:
            more = more.strip()

        if key is None:
            return
        if key in self.cases:
            return self.cases[key](self, key, value, more)

        path = self.key2path(key)

        for ftest, ffix in self.value_cases.iteritems():
            if ftest(value):
                value = ffix(self, value)

        N = len(path)
        for depth,cases in self.key_cases.iteritems():
            if depth>=N: break
            if path[depth] in cases:
                return cases[path[depth]](self, path, value, more)

        self.set(path, value)

        if more and len(more):
            return self.parse_line(more)
