"""
Adds support for persisting into a new graphical shell, instead of
just the current shell
"""
from subprocess import call
from mush import interfaces


class persist_shell(interfaces.persist_shell):
    __keyname__ = "guake"
    __api_visible__ = False

    @staticmethod
    def persist(env, *args, **kwargs):
        alias = kwargs.get('alias', '')
        cmd = 'guake -n {tabname}; guake -r {tabname}'.format(tabname=alias)
        exp_env = ['export "{}={}"'.format(k,v) for k, v in env.items()]
        print exp_env
        exit()
        env_export_cmd = ';'.join()
        cmd = "guake -n {tabname}; guake -r {tabname} -e '{env_export_cmd}'".format(tabname=alias, env_export_cmd=env_export_cmd)
        call(cmd, shell=True)
