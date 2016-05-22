from mush import engine


class persist_shell(engine.AutoRegisteringPlugin):
    __interface__ = 'persist_shell'

    @staticmethod
    def persist(*args, **kwargs):
        raise NotImplementedError


class access_secret(engine.AutoRegisteringPlugin):
    __interface__ = 'access_secret'
    __api_visible__ = False

    def __call__(self, value):
        raise NotImplementedError


class data_store(engine.AutoRegisteringPlugin):
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
