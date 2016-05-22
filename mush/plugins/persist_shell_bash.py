"""
Adds support for persisting into a new graphical shell, instead of
just the current shell
"""
from subprocess import call
from mush import interfaces


class persist_shell(interfaces.persist_shell):
    __keyname__ = "bash"

    @staticmethod
    def persist(env, *args, **kwargs):
        call('bash', env=env)
