# Read in the mush config so we can set default plugins
import os
import ConfigParser

_cfgpath = os.path.abspath(os.path.expanduser('~/.mush/config'))
_localpath = os.path.abspath(os.path.expanduser('./.mush/config'))
if os.path.exists(_localpath):
    _cfgpath = _localpath
_config = ConfigParser.RawConfigParser()
_config.read(_cfgpath)

def check(append_failmsg=None):
    """Try loading the default config section, return a failure message on
    failure"""
    try:
        resp = _config.get('default_plugins', 'data_store')
    except ConfigParser.NoSectionError:
        return (
            'Could not find a [default_plugins] section in the '
            'mush config located at {}'.format(_cfgpath))

def get(interface, keyname, key, defaults=None):
    try:
        return _config.get("{}.{}".format(interface, keyname), key)
    except ConfigParser.NoSectionError:
        defaults = defaults or dict()
        return defaults.get(key)

def get_default(interface, key):
    """Returns the value of the key for the default implementation of the
    provided interface, as defined in the 'default_plugins' section in 
    the mush config file"""
    section = "{}.{}".format(
        interface, _config.get('default_plugins', interface))
    return _config.get(section, key)
