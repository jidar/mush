#! /usr/bin/python
import csv
import os
import sys
import prettytable
from subprocess import call, Popen, PIPE, CalledProcessError
from collections import OrderedDict

from mush.config import config
from mush.plugins import api

# TODO: Maybe make this an auto interface like plugins.api
class CLI(object):

    @classmethod
    def _command_names(cls, python_names=False):
        cmds = []
        for k, v in cls.__dict__.items():
            try:
                if cls._command in v.__mro__ and v.__name__ != '_command':
                    name = k if python_names else k.replace('_', '-')
                    cmds.append(name)
            except Exception as e:
                pass

        # Remove all hidden commands
        #[cmds.remove(cmd) for cmd in cmds if cmd.startswith(('-','_',))]
        return cmds

    class _command(object):
        """All CLI commands should inherit from this, for reasons."""

        __known_flags__ = []

        @classmethod
        def _call(cls, data_store, aliases, *args):
            raise NotImplementedError

        @classmethod
        def help(cls, *args, **kwargs):
            return  cls.__doc__

        @classmethod
        def check_aliases(cls, aliases):
            if len(aliases) < 1:
                print cls.help()
                cls.fail('No aliases entered')

        @classmethod
        def check_flags(cls, flags):
            bad_flags = [f for f in flags if f not in cls.__known_flags__]
            if bad_flags:
                print cls.help()
                cls.fail(
                    'Unknown flag{}: {}'.format(
                        's' if len(bad_flags)>1 else '',\
                        ", ".join(bad_flags)))

        @classmethod
        def fail(cls, reason=None, help=True):
            cls.help()
            print reason
            exit(-1)

        @classmethod
        def finish(cls, reason=None, help=False):
            print reason
            exit(0)


    @classmethod
    def _dispatch(cls, cmd, data_store, aliases, args, flags):
        """Processes command arguments and returns the proper function"""

        # replace dashes with underscores (to support names with - in them)
        cmd = cmd.replace('-', '_')

        # Only allow calls to _command objects
        command = getattr(cls, cmd)
        exception = None

        if cls._command in command.__mro__ and command.__name__ != '_command':

            if flags.get('help'):
                print command.help(data_store, aliases, args, flags)
                exit(0)

            if command.__known_flags__:
                command.check_flags(flags)
            return command._call(data_store, aliases, args, flags)


    class help(_command):
        """ Dynamically generates help based on the help() functions
        defined in each _command class.  By default, the help() methods
        return the docstring of the command class...which is why you're seeing
        this message right now.  Who calls 'help --help' anyway?!"""

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            spacer = "    "
            helplines = []
            helplines.append("")
            helplines.append("{0}OS Command Passthrough:".format(spacer))
            helplines.append(
                "{0}mush <alias(es)> [--flags] <client> "
                "[client command passthrough]\n"
                .format(spacer))
            helplines.append("{0}Mush commands:".format(spacer))
            helplines.append(
                "{0}mush <command> [alias(es)] [--flags] <client> "
                "[client command passthrough]\n"
                .format(spacer))
            cmds = CLI._command_names(python_names=True)
            cmds.remove('help')
            for name in cmds:
                helplines.append(
                    "{0}{1}".format(spacer, name.replace('_','-')))
                helpdoc = getattr(CLI, name).help()
                helplines.append("{0}{1}\n".format(spacer*2, helpdoc))
            print "\n".join(helplines)


    class aliases(_command):
        """Lists all available aliases in the datastore"""

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            print "\n".join(data_store.available_aliases())


    class datastore(_command):
        """Output a list of all environment variables the user/alias has
        defined.  By default this is a list of strings.

        <alias(es)>:  Requires at least one alias.
        --exportable  Display the environment vars such that you can copy
                      them and paste them as a bash command.
        --table       Display the environment vars in a pretty table.
        --show-blanks Also display keys that have no configured value
                      (By default, those keys are not show)
        --keys-only   Only display keys
        --detail=<keys>
                      Display only the keys specififed, and their values
        """
        __known_flags__ = [
            'show-blanks', 'detail', 'keys-only', 'exportable', 'table']

        @classmethod 
        def target_keys(cls, flags, env_vars):
            if not flags.get('show-blanks'):
                env_vars = OrderedDict(
                    (k, v) for k, v in env_vars.iteritems() if v)

            if flags.get('detail'):
                keys = flags.get('detail').split(',')
                env_vars = {k:v for k,v in env_vars.items() if k in keys}

            if flags.get('keys-only'):
                env_vars = {k:'' for k in env_vars.keys()}

            return env_vars

        @classmethod
        def exportable(cls, alias, env_vars):
            print "\n","#", alias.upper()
            for k,v in env_vars.iteritems():
                print "export {}={}".format(k,v)

        @classmethod
        def plaintext_list(cls, alias, env_vars):
            print "-" * 30
            print alias.upper()
            for k,v in env_vars.iteritems():
                print k, v

        @classmethod
        def table(cls, alias, env_vars):
            p = prettytable.PrettyTable(
                    field_names=["Environment Variable", "Value"])
            [p.add_row((k,v,)) for k,v in env_vars.iteritems()]
            print "\n", alias.upper()
            print p

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            cls.check_aliases(aliases)
            for alias in aliases:
                env_vars = cls.target_keys(
                    flags, data_store.environment_variables(alias))

                if flags.get('exportable'):
                    cls.exportable(alias, env_vars)

                if flags.get('table'):
                    cls.table(alias, env_vars)
                
                if not flags.get('table') and not flags.get('exportable'):
                    cls.plaintext_list(alias, env_vars)

    class persist(_command):
        """Spawn a new shell with all the environment variables set for 
        the given user/alias.

        --shell <plugin>: Override configured persist-shell command.
        --shellcmd <cmd>: Ignore any installed plugins and try to run this
                          command directly.  (Not Recommended)
        """
        __known_flags__ = ['shellcmd', 'shell']

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            cls.check_aliases(aliases)
            env = os.environ.copy()
            if flags.get('shellcmd'):
                call(flags.get('shellcmd'), env=env)
            else:
                for alias in aliases:
                    env.update(data_store.environment_variables(alias))
                    plugin = flags.get('shell', 'gnome-terminal')
                    api.persist_shell(keyname=plugin).persist(env)


    class call(_command):
        """Calls client command once for every alias listed

        Note: This is the default command called, you don't need to specify
        'call', you can just run 'mush <alias(es)> <client command>

        <alias(es)>:  Requires at least one alias.
        --no-stderr:  Pipes the stderr output from the client command
                      to the system's version of /dev/null
        --show-alias: Prints the alias used before making the client call.
                      Useful when making calls to multiple aliases.
        """
        __known_flags__ = ['show-alias', 'no-stderr']

        @classmethod
        def _dispatch_to_shell(cls, cmd, data_store, alias, args, flags):
            stderr_out = \
                open(os.devnull, 'w') if flags.get('no-stderr') else sys.stderr
            env = os.environ.copy()
            user_env = data_store.environment_variables(alias)
            env.update(user_env)
            cmd = "{} {}".format(cmd, " ".join(args))
            call(cmd, stdout=sys.stdout, stderr=stderr_out, shell=True, env=env)

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            cls.check_aliases(aliases)
            args = list(args)
            cmd = args[0]
            args.remove(cmd)

            for alias in aliases:
                if flags.get('show-alias'):
                    print "### {0} ###".format(alias)
                cls._dispatch_to_shell(
                    cmd, data_store, alias, args,
                    {'no-stderr': flags.get('no-stderr')})

    # class generate_config(_command):
    #     """Generates a configuration file based on available plugins"""

    #     @classmethod
    #     def _call(cls, data_store, aliases, args, flags):
    #         from mush.plugins.interfaces import registry
    #         for interface in registry.plugins().keys():
    #             print ''
    #             for keyname in registry.plugins(interface):
    #                 string = "[{}.{}]".format(interface, keyname)
    #                 print string


def entry_point():
    args = sys.argv
    args.remove(args[0])

    data_store = api.data_store()
    mush_command = None
    client_command = None
    aliases = []
    flags = {}

    # Run Help if nothing else was passed in
    if not args:
        CLI._dispatch("help", data_store, aliases, args, flags)
        exit(0)

    # Check if the first arg is a mush command, and pull it out if it is
    if args[0] in CLI._command_names():
        mush_command = args[0]
        args.remove(args[0])

    known_aliases = data_store.available_aliases()
    # Parse out the rest of the args, seperating aliases from flags
    # and the client command / client command args
    while args:
        arg = args[0]
        args.remove(arg)

        if arg in known_aliases:
            aliases.append(arg)
            continue

        if arg.startswith('--'):
            # Grab mush flags
            arg = arg.lstrip('--')
            val = arg.split('=', 1)
            arg = val[0]
            val = val[1] if len(val) == 2 else True
            flags[arg] = val
            continue

        # if we hit a non-alias, non-flag, assume it's the
        # start of the client command
        client_command = arg
        break

    if not client_command and not mush_command:
        args, flags, mush_command = [], {}, "help"
    elif client_command and not mush_command:
        args.insert(0, client_command)
        mush_command = "call"

    CLI._dispatch(mush_command, data_store, aliases, args, flags)
