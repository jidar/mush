"""
Adds support for persisting into a new graphical shell, instead of
just the current shell
"""
from subprocess import call
from mush.plugins import interfaces


class persist_shell(interfaces.persist_shell):
    __keyname__="guake"

    @staticmethod
    def persist(env, *args, **kwargs):
        alias = kwargs.get('alias', '')
        cmd = 'guake -n {tabname}; guake -r {tabname}'.format(tabname=alias)
        call(cmd, env=env, shell=True)
