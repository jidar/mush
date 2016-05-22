from subprocess import Popen, PIPE
from mush import interfaces


class access_secret(interfaces.access_secret):
    __keyname__ = "exec_bash"
    __config_defaults__ = {'magic_prefix': 'EXEC_BASH:'}

    def __call__(self, environment_variables):
        prefix = self.cfg("magic_prefix")
        for k, v in environment_variables.iteritems():
            if v.startswith(prefix):
                cmd = v.replace(prefix, '')
                p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
                std_out, std_err = p.communicate()
                if std_err and p.returncode:
                    print "exec_bash exited with a non-zero return code"
                    print std_err
                    return environment_variables
                environment_variables[k] = str(std_out).splitlines()[0]
        return environment_variables
