import os
import sys
from collections import OrderedDict

try:
    import ConfigParser
except:
    import configparser as ConfigParser

from mush import engine, interfaces


class data_store(interfaces.data_store):
    __keyname__ = "supernova"
    __config_defaults__ = {"location": os.path.expanduser("~/.supernova")}

    def __init__(self):
        possible_configs = [self.cfg('location'), '.supernova']
        self.supernova_config = ConfigParser.SafeConfigParser()
        try:
            self.supernova_config.read(possible_configs)
        except:
            msg = """
A valid supernova configuration file is required.
Ensure that you have a properly configured supernova configuration file called
'.supernova' in your home directory or in your current working directory.
"""
            print(msg)
            sys.exit(1)

    @engine.fallthrough_pipeline('access_secret')
    def environment_variables(self, alias):
        # Extract the relevant environment variables for alias
        env_vars = OrderedDict()
        for k, v in self.supernova_config.items(alias):
            env_vars[k.upper()] = v
        return env_vars

    def available_aliases(self):
        return self.supernova_config.sections()
