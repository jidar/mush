#! /usr/bin/python
import csv
import os
import sys
import prettytable
from subprocess import call, Popen, PIPE, CalledProcessError
from collections import OrderedDict

from mush.config import config
from mush.plugins import api

#Global commands
def _remove_empty_kv_pairs(dictionary):
    return OrderedDict((k, v) for k, v in dictionary.iteritems() if v)

def dispatch_to_shell(cmd, data_store, alias, args, suppress_stderr=False):
    stderr_out = open(os.devnull, 'w') if suppress_stderr else sys.stderr
    env = os.environ.copy()
    user_env = data_store.environment_variables(alias)
    env.update(user_env)
    cmd = "{} {}".format(cmd, " ".join(args))
    call(cmd, stdout=sys.stdout, stderr=stderr_out, shell=True, env=env)


# Commands
class CLI(object):

    @classmethod
    def _command_names(cls, python_names=False):
        cmds = []
        for k, v in cls.__dict__.items():
            try:
                if cls._command in v.__mro__:
                    name = k if python_names else k.replace('_', '-')
                    cmds.append(name)
            except Exception as e:
                pass

        # Remove all hidden commands
        [cmds.remove(cmd) for cmd in cmds if cmd.startswith(('-','_',))]
        return cmds

    class _command(object):
        """All CLI commands should inherit from this, for reasons."""

        @classmethod
        def _call(cls, data_store, aliases, *args):
            raise NotImplementedError

        @classmethod
        def help(cls, *args, **kwargs):
            return  cls.__doc__

        @classmethod
        def check_aliases(cls, *aliases):
            if not aliases:
                cls.fail('No aliases entered')

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
    def _process(cls, cmd, data_store, aliases, args, flags):
        """Processes command arguments and returns the proper function"""

        # replace dashes with underscores (to support names with - in them)
        cmd = cmd.replace('-', '_')

        # Only allow calls to _command objects
        command = getattr(cls, cmd)
        exception = None

        if cls._command in command.__mro__:

            if flags.get('help'):
                print command.help(data_store, aliases, *args, **flags)
                exit(0)

            return command._call(data_store, aliases, *args, **flags)

    class help(_command):
        """ Dynamically generates help based on the help() functions
        defined in each _command class.  By default, the help() methods
        return the docstring of the command class...which is why you're seeing
        this message right now.  Who calls 'help --help' anyway?!"""

        @classmethod
        def _call(cls, data_store, aliases, *args, **flags):
            spacer = "    "
            helplines = []
            helplines.append("mush")
            helplines.append("{0}OS Command Passthrough:".format(spacer))
            helplines.append(
                "{0}mush <alias> <client> [client command passthrough]\n"
                .format(spacer))
            helplines.append("{0}Mush commands:".format(spacer))
            helplines.append(
                "{0}mush <command> [aliases] [--flags] <client> "
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


    class list(_command):
        """Lists all available aliases in the datastore"""

        @classmethod
        def _call(cls, data_store, aliases, *args, **flags):
            print "\n".join(data_store.available_aliases())


    class show(_command):
        """Output a list of all environment variables the user/alias has
        defined.  By default this is a list of strings.
        --exportable:  Display the environment vars such that you can copy
                       them and paste them as a bash command.
        --table:       Display the environment vars in a pretty table.
        """

        @classmethod
        def _call(cls, data_store, aliases, *args, **flags):
            cls.check_aliases(aliases)
            for alias in aliases:
                env_vars = _remove_empty_kv_pairs(
                    data_store.environment_variables(alias))

                if flags.get('exportable'):
                    print "\n","#", alias.upper()
                    for k,v in env_vars.iteritems():
                        print "export {}={}\n".format(k,v)

                elif flags.get('table'):
                    env_vars = _remove_empty_kv_pairs(
                        data_store.environment_variables(alias))
                    p = prettytable.PrettyTable(
                            field_names=["Environment Variable", "Value"])
                    [p.add_row((k,v,)) for k,v in env_vars.iteritems()]
                    print p

                else:
                    # Regular list
                    print "-" * 30
                    for k,v in env_vars.iteritems():
                        print k, v

    class persist(_command):
        """Spawn a new shell with all the environment variables set for 
        the given user/alias.

        --shell <plugin>: Override configured persist-shell command.
        --shellcmd <cmd>: Ignore any installed plugins and try to run this
                          command directly.  (Not Recommended)
        """

        @classmethod
        def _call(cls, data_store, aliases, *args, **flags):
            cls.check_aliases(aliases)
            env = os.environ.copy()
            if flags.get('shellcmd'):
                call(flags.get('shellcmd'), env=env)
            else:
                for alias in aliases:
                    env.update(data_store.environment_variables(alias))
                    plugin = flags.get('shell', 'gnome-terminal')
                    api.persist_shell(keyname=plugin).persist(env)


    class multicall(_command):
        """Calls client command once for every alias listed
        --suppress-stderr:  Pipes the stderr output from the client command
                            to the system's version of /dev/null
        """

        @classmethod
        def _call(cls, data_store, aliases, *args, **flags):
            cls.check_aliases(aliases)
            args = list(args)
            cmd = args[0]
            args.remove(cmd)

            for alias in aliases:
                dispatch_to_shell(
                    cmd, data_store, alias, args,
                    suppress_stderr=flags.get('suppress_stderr', None))


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
        CLI._process("help", data_store, aliases, args, flags)
        exit(0)

    # Check if the first arg is a mush command, and pull it out if it is
    if args[0] in CLI._command_names():
        mush_command = args[0]
        args.remove(args[0])

    # The next arg should be an alias
    known_aliases = data_store.available_aliases()
    while args:
        arg = args[0]
        args.remove(arg)
        if arg in known_aliases:
            aliases.append(arg)
        elif arg.startswith('--'):
            # Grab mush flags
            arg = arg.lstrip('--')
            val = arg.split('=')
            arg = val[0].replace('-','_')
            if len(val) > 1:
                val = val[1]
            else:
                val = True
            flags[arg] = val
        else:
            # if we hit a non-alias, non optional arg, assume it's the
            # start of the client command
            client_command = arg
            break

    # Dispatch to shell if no mush commands, and only a single alias
    # is present like so:
    # mush myalias nova list
    if mush_command:
        if client_command:
            args.insert(0, client_command)
        CLI._process(mush_command, data_store, aliases, args, flags)
    elif not mush_command and len(aliases)==1 and client_command:
        dispatch_to_shell(client_command, data_store, aliases[0], args, flags)
    else:
        CLI._process("help", data_store, aliases, [], {})

