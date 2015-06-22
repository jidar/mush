# Read in the mush config so we can set default plugins
import os
from ConfigParser import SafeConfigParser

cfgpath = os.path.abspath(os.path.expanduser('~/.mush/config'))
localpath = os.path.abspath(os.path.expanduser('./.mush/config'))
if os.path.exists(localpath):
    cfgpath = localpath
config = SafeConfigParser()
config.read(cfgpath)

def default(interface, key):
    section = "{}.{}".format(
        interface, config.get('default_plugins', interface))
    return config.get(section, key)
