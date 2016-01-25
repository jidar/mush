from mush import config


# Stores all registered extensions in this module
class _Registry(dict):

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

registry = _Registry()
registry['interfaces'] = list()
registry['plugins'] = dict()


def fallthrough_pipeline(*pipeline_interfaces):
    def decorator(function):
        def wrapper(*args, **kwargs):
            val = function(*args, **kwargs)
            for interface_name in pipeline_interfaces:
                for keyname in registry.keynames(interface_name):
                    plugin = registry.plugin(interface_name, keyname)
                    if plugin:
                        val = plugin()(val)
            return val
        return wrapper
    return decorator


class _AutoRegisteringPluginMeta(type):
    """Plugin interfaces should metaclass from this class in order to be
    registered as an implementation of their target interface."""

    def __new__(cls, class_name, bases, attrs):
        plugin = super(_AutoRegisteringPluginMeta, cls).__new__(
            cls, class_name, bases, attrs)

        # Register interface implementations (aka, 'plugins')
        if plugin.__keyname__ and plugin.__interface__:
            registry['plugins'][plugin.__interface__] = \
                registry['plugins'].get(plugin.__interface__, dict())
            registry['plugins'][plugin.__interface__][plugin.__keyname__]\
                = plugin
        elif not plugin.__keyname__ and plugin.__interface__:
            registry['interfaces'].append(plugin)

        return plugin


class AutoRegisteringPlugin(object):
    __metaclass__ = _AutoRegisteringPluginMeta
    __keyname__ = None
    __interface__ = None
    __api_visible__ = True
    __config_defaults__ = {}

    @classmethod
    def cfg(cls, key):
        return config.get(
            cls.__interface__, cls.__keyname__, key,
            defaults=cls.__config_defaults__)


class persist_shell(AutoRegisteringPlugin):
    __interface__ = 'persist_shell'

    @staticmethod
    def persist(*args, **kwargs):
        raise NotImplementedError


class access_secret(AutoRegisteringPlugin):
    __interface__ = 'access_secret'
    __api_visible__ = False

    def __call__(self, value):
        raise NotImplementedError


class data_store(AutoRegisteringPlugin):
    __interface__ = 'data_store'
    __config_defaults__ = {'location': None}

    def __init__(self, data_file=None):
        raise NotImplementedError

    def environment_variables(self, alias):
        """Must accept a single string. Returns an OrderedDict"""
        raise NotImplementedError

    def aliases(self):
        """Returns a List"""
        raise NotImplementedError
