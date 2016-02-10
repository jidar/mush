import keyring
from mush import interfaces


class access_secret(interfaces.access_secret):
    __keyname__ = "python_keyring"
    __config_defaults__ = {'magic_prefix': 'KEYRING:', 'service': 'mush'}

    def __call__(self, environment_variables):
        magic_prefix = self.cfg("magic_prefix")
        service_name = self.cfg("service")

        for key, val in environment_variables.iteritems():
            if val.startswith(magic_prefix):
                keyring_key = val.replace(magic_prefix, '')
                keyring_val = None
                try:
                    keyring_val = keyring.get_password(
                        service_name, keyring_key)
                except Exception as e:
                    print e
                    environment_variables[key] = val
                environment_variables[key] = keyring_val
        return environment_variables
