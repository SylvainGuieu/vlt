from os.path import *

def find(name, path=None, prefix=None, extention=None, defaults={}):
    path   = defaults.get('path',[]) if path is None else path
    prefix = defaults.get('prefix',"") if prefix is None else prefix
    extention = defaults.get("extention", "") if extention is None else extention

    if extention and not name.endswith("."+extention):
        name += "."+extention
    if prefix and not name.startswith(prefix):
        name = prefix+name

    for directory in path:
        file_path = join(directory, name)
        if exists(file_path):
            return file_path
    raise ValueError("cannot find file {0} in any of the path: {1}".format(name, path))        
        