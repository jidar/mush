import os
import ConfigParser


class config(object):
    _cfgpath = os.path.abspath(os.path.expanduser('~/.mush/config'))
    _localpath = os.path.abspath(os.path.expanduser('./.mush/config'))
    if os.path.exists(_localpath):
        _cfgpath = _localpath
    _config = ConfigParser.RawConfigParser()
    _config.read(_cfgpath)

    @classmethod
    def check(cls, append_failmsg=None):
        """Try loading the default config section, return a failure message on
        failure"""
        try:
            cls._config.get('default_plugins', 'data_store')
        except ConfigParser.NoSectionError:
            return (
                'Could not find a [default_plugins] section in the '
                'mush config located at {}'.format(cls._cfgpath))

    @classmethod
    def get(cls, interface, keyname, key, defaults=None):
        try:
            return cls._config.get("{}.{}".format(interface, keyname), key)
        except ConfigParser.NoSectionError:
            defaults = defaults or dict()
            return defaults.get(key)

    @classmethod
    def get_default(cls, interface, key):
        """Returns the value of the key for the default implementation of the
        provided interface, as defined in the 'default_plugins' section in
        the mush config file"""
        section = "{}.{}".format(
            interface, cls._config.get('default_plugins', interface))
        return cls._config.get(section, key)


class Registry(dict):

    def __init__(self):
        self['interfaces'] = list()
        self['plugins'] = dict()

    def interface(self, interface_name):
        return self.get('interfaces').get(interface_name)

    def interfaces(self):
        return self.get('interfaces')

    def plugins(self, interface_name=None):
        if interface_name:
            return self.get('plugins').get(interface_name)
        return self.get('plugins')

    def plugin(self, interface_name, keyname):
        return self.get('plugins').get(interface_name).get(keyname)

    def keynames(self, interface_name):
        return self.get('plugins').get(interface_name).keys()

# Stores all registered extensions in this module
registry = Registry()


def fallthrough_pipeline(*pipeline_interfaces):
    def decorator(function):
        def wrapper(*args, **kwargs):
            global registry
            val = function(*args, **kwargs)
            for interface_name in pipeline_interfaces:
                for keyname in registry.keynames(interface_name):
                    plugin = registry.plugin(interface_name, keyname)
                    if plugin:
                        val = plugin()(val)
            return val
        return wrapper
    return decorator


class AutoRegisteringPluginMeta(type):
    """
    Plugin interfaces should metaclass from this class in order to be
    registered as an implementation of their target interface.
    """

    def __new__(cls, class_name, bases, attrs):
        plugin = super(AutoRegisteringPluginMeta, cls).__new__(
            cls, class_name, bases, attrs)

        # Register interface implementations (aka, 'plugins')
        global registry
        if plugin.__keyname__ and plugin.__interface__:
            registry['plugins'][plugin.__interface__] = \
                registry['plugins'].get(plugin.__interface__, dict())
            registry['plugins'][plugin.__interface__][plugin.__keyname__]\
                = plugin
        elif not plugin.__keyname__ and plugin.__interface__:
            registry['interfaces'].append(plugin)

        return plugin


class AutoRegisteringPlugin(object):
    __metaclass__ = AutoRegisteringPluginMeta
    __keyname__ = None
    __interface__ = None
    __api_visible__ = True
    __config_defaults__ = {}

    @classmethod
    def cfg(cls, key):
        global config
        return config.get(
            cls.__interface__, cls.__keyname__, key,
            defaults=cls.__config_defaults__)
