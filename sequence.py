
_loop_class = (list, tuple)

def sequence(func, *args, **kwargs):
    """ built a sequence object on one function

    Args:
        func : the function to execute
        *args : function argument if list or tuple they are cycled
        **kwargs function kwargs, list/ tuple are cycled as well

    """
    return Sequence( (func, args, kwargs), modulo=True )
def sequences(*m_args, **options):
    return Sequence( *m_args, **options)

class Sequence(object):
    def __init__(self, *m_args, **options):

        self.m_args = self._check_m_args(m_args)
        self.counter = -1
        size = options.pop("size", None)
        modulo = options.pop("modulo",False)
        if len(options):
            raise KeyError("Accept only size and modulo keywords")
        if modulo:
            self.size = self.getMaxLen() if size is None else size
        else:
            self.size = self.checkLens(size)

    def getMaxLen(self):
        n = 0
        for m,args,kwargs in self.m_args:
            for k,p in kwargs.iteritems():
                if issubclass(type(p), _loop_class):
                    n = max(n,len(p))
            for p in args:
                if issubclass(type(p), _loop_class):
                    n = max(n,len(p))
        return n or 1

    def checkLens(self, size):

        for m,args,kwargs in self.m_args:
            for k,p in kwargs.iteritems():
                if issubclass(type(p), _loop_class):
                    if size is None:
                        size = len(p)
                    elif len(p)!=size:
                        raise ValueError("list for keyword %s does not have the right len expected %d got %d"%(k,size,len(p)))

            for p in args:
                if issubclass(type(p), _loop_class):
                    if size is None:
                        size = len(p)
                    elif len(p)!=size:
                        raise ValueError("list for args num %d does not have the right len expected %d got %d"%(args.index(p),size,len(p)))

        return size


    def call(self):
        return self.rebuildMethodKwargs()

    @staticmethod
    def _check_m_args(m_args):
        out = []
        for m_a in m_args:
            if not issubclass( type(m_a), tuple):
                raise ValueError("Arguments must be tuple of one two or three")
            Nm_a = len(m_a)
            if Nm_a<1:
                raise ValueError("Empty tuple")

            if not hasattr( m_a[0], "__call__"):
                raise ValueError("first element of tuple must have a call method (a function ro class)")
            if Nm_a<2:
                args, kwargs = [], {}
            elif Nm_a<3:
                args , kwargs = m_a[1], {}
                if issubclass( type(args), dict): # reverse args and kwargs
                    args, kwargs = [], args

            elif Nm_a<4:
                args , kwargs = m_a[1:3]
            else:
                raise ValueError("tuple must have one two or three elements")
            if issubclass( type(args), dict): # reverse args and kwargs
                args, kwargs = kwargs, args
            if issubclass( type(args), dict) or issubclass( type(kwargs), (list,tuple)):
                raise ValueError("tuple must contain at least a method then a list or a dict or both")
            out.append( (m_a[0], args, kwargs.copy()))
        return out

    def rebuildMethodKwargs(self):
        out = []
        for m,a,kw in self.m_args:
            out.append( (m, self.rebuildArgs(a), self.rebuildKwargs(kw) ) )
        return MethodArgsList(out)

    def rebuildKwargs(self, kwargs):
        kout = kwargs.copy()
        for k,v in kwargs.iteritems():
            if issubclass( type(v), _loop_class):
                kout[k] = v[self.counter%len(v)]
        return kout

    def rebuildArgs(self, args):
        aout = []
        for a in args:
            if issubclass( type(a), _loop_class):
                aout.append(a[self.counter%len(a)])
            else:
                aout.append(a)
        return aout

    def next(self):
        if self.counter>=(self.size-1):
            raise StopIteration()
        self.counter += 1
        return self.call()

    def __iter__(self):
        self.counter = -1
        return self

    def go(self):
        return [ l.call() for l in self]

    def control(self):
        for l in self:
            l.control()



class MethodArgsList(list):
    def call(self):
        out = []
        for method,args,kwargs in self:
            #if len(kwargs) and "kwargs" in method.im_func.func_code.co_varnames:
            #    tmp = method(*args, kwargs=kwargs)
            #else:
            tmp = method(*args, **kwargs)
            out.append(tmp)
        return out
    def control(self):
        for method,args,kwargs in self:
            print method,args,kwargs


