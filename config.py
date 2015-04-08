"""
Configuration file of the vlt package. to be change with cotion
"""
import os


def env_path(env, relative_path):
    """
    env_path( env, relative_path)
    return [ os.getenv(env)/relative_path ]
    or [] if os.getenv(env) is None or if the

    """
    env_dir = os.getenv(env)
    if env_dir is None:
        return []
    if relative_path is None:
        path = env_dir
    else:
        path = env_dir.rstrip("/") + "/" + relative_path.strip("/")
    if not os.path.exists(path):
        print "WARNING VLT CONFIG: the path '%s' does not exists " % path
    return [path]



def get_or_create_directory(path):
    """ return the diretory path but create it if not exists """
    if os.path.exists(path):
        return path
    os.makedirs(path)
    return path


def package_dir(relative_path):
    """
    get the path relative to this package.
    if the path does not exists it is created
    """
    package_dir = os.path.dirname(__file__)
    path = package_dir + "/" + relative_path.strip("/")
    return get_or_create_directory(path)


config = {
    # list of directories containing the CDT files
    "cdtpath": env_path("INTROOT", "CDT"),

    # list of directory where cdt temporaly py file will be
    # created
    "cdtpydir": package_dir("processes"),
    # boolean value for cdt debug
    "cdtdebug": False,

    # list of directories containing the dictionary files
    "dictionarypath": env_path("INS_ROOT", "SYSTEM/Dictionary")+
                      env_path("VLTROOT", "config"),
    # if key_match_case is true, the Function anf FunctionDict objects
    # becomes case sensitive meaning that, e.g, dcs["DIT"] != dcs["dit"]
    # default is false
    "key_match_case": False
}

# debug local configuration
config["cdtpath"] += ["/Users/guieu/python/vlt/CDT"]
config["dictionarypath"] += ["/Users/guieu/python/vlt/Dictionary",
                             "/Users/guieu/python/vlt/Dictionary/CCSLite"
        ]


