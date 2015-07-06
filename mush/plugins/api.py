"""
Automatically builds the api from the available interface implementations 
"""
import pkgutil
from mush import plugins
from mush import config
from mush.plugins import interfaces
__loaded__ = False

class _APICallClass(object):

    def __init__(self, interface):
        self.interface = interface

    def __call__(self, *args, **kwargs):
        keyname = config._config.get('default_plugins', self.interface)
        if kwargs.get('keyname'):
            keyname = kwargs.get('keyname')
            kwargs.pop('keyname')
        return interfaces.registry['plugins'][self.interface].get(keyname)(
            *args, **kwargs)


def load(plugin_paths=None):
    plugin_paths = plugin_paths or list()

    def path_generator(*paths):
        for p in paths:
            for loader, module_name, is_pkg in pkgutil.walk_packages(p):
                yield loader, module_name, is_pkg

    # Identify, recursively, every module in the target cafe package
    for loader, module_name, is_pkg in path_generator(*plugin_paths):
        # Import the current module
        if '_plugins' in module_name:
            try:
                module = loader.find_module(module_name).load_module(module_name)
            except Exception as exception:
                print "Unable to load plugin ", module.__name__
                print exception
                continue

# Load plugin modules
if not __loaded__:
    load([plugins.__path__])
    __loaded__ = True


# Build API
for interface_class in interfaces.registry.get('interfaces'):
    if interface_class.__api_visible__:
        globals()[interface_class.__name__] = _APICallClass(
            interface_class.__interface__)
