from collections import OrderedDict
from subprocess import call, Popen, PIPE, CalledProcessError
import os

from mush.config import config

# Stores all registered extensions in this module
class _Registry(dict):

    def interfaces(self):
        return self.get('interfaces')

    def plugins(self):
        return self.get('plugins')

    def keynames(self, interface_name):
        if interface_name:
            return self.get('plugins').get(interface_name).keys()

registry = _Registry()
registry['interfaces'] = list()
registry['plugins'] = dict()


class _AutoRegisteringPluginMeta(type):
    """Plugin interfaces should metaclass from this class in order to be 
    registered as an implementation of their target interface."""

    def __new__(cls, class_name, bases, attrs):
        plugin = super(_AutoRegisteringPluginMeta, cls).__new__(
            cls, class_name, bases, attrs)

        if plugin.__keyname__ and plugin.__interface__:
            registry['plugins'][plugin.__interface__] = \
                registry['plugins'].get(plugin.__interface__, dict())
            registry['plugins'][plugin.__interface__][plugin.__keyname__]\
                =plugin
        elif not plugin.__keyname__ and plugin.__interface__:
            registry['interfaces'].append(plugin)
        return plugin


class AutoRegisteringPlugin(object):
    __metaclass__ = _AutoRegisteringPluginMeta
    __keyname__ = None
    __interface__ = None


class persist_shell(AutoRegisteringPlugin):
    __interface__ = 'persist_shell'

    @staticmethod
    def persist(env):
        raise NotImplementedError


class data_store(AutoRegisteringPlugin):
    """implementer should define __keyname__"""
    __interface__ = 'data_store'

    def __init__(self, data_file=None):
        raise NotImplementedError

    def configured_data_file(self):
        return os.path.expanduser(config.get('data_store.csv', 'location'))

    def environment_variables(self, alias):
        """Must accept a single string. Returns an OrderedDict"""
        raise NotImplementedError

    def aliases(self):
        """Returns a List"""
        raise NotImplementedError

    # TODO: Implement an pipeline extension mechanism, inject an extension
    # point in environment_variables, and reimplement this as a default 
    # extension. This comment is also in the default plugin.
    def exec_bash(self, environment_variables):
        for k,v in environment_variables.iteritems():
            if v.startswith('EXECBASH:'):
                cmd = v.replace('EXECBASH:', '')
                p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
                std_out, std_err = p.communicate()
                if std_err and p.returncode:
                    print "EXECBASH command exited with a non-zero return code"
                    print std_err
                    exit(p.returncode)
                environment_variables[k] = str(std_out).splitlines()[0]
        return environment_variables
