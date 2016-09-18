
class Actions(object):
    def __init__(self, *args, **kw):
        parent = kw.pop("parent",None)
        if len(kw):
            raise KeyError("Actions take only 'parent' has keyword")

        self.actions = {}
        self.actionCounter = 0
        self.stopped = False
        self.parent = parent
        for action in args:
            self.addAction(action)

    def stop(self):
        self.stopped = True
    def release(self):
        self.stopped = False


    def addAction(self, action):
        if not hasattr(action, "__call__"):
            raise ValueError("action must have a __call__attribute")
        self.actionCounter += 1
        self.actions[self.actionCounter] = action
        return self.actionCounter

    def remove(self, id):
        if not id in self.actions:
            raise KeyError("Cannot find an action connected with id %s"%id)

        del self.actions[id]
    def pop(self, id, default=None):
        return self.actions.pop(id, default)

    def clear(self):
        return self.actions.clear()

    def run(self, *args, **kwargs):
        if self.stopped: return
        if not self.actionCounter: return
        if self.parent:
            self.parent.run(*args, **kwargs)

        keys = self.actions.keys()
        keys.sort()
        for k in keys:
            self.actions[k](*args, **kwargs)

    def copy(self):
        return self.__class__( **self.actions )

    def derive(self):
        return self.__class__(parent=self)

    def __len__(self):
        if self.parent:
            return len(self.parent) + len(self.actions)
        return len(self.actions)

    def __call__(self, action):
        return self.addAction(action)
