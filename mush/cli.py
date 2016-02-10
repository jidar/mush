#! /usr/bin/python
import os
import prettytable
import sys
from collections import OrderedDict
from subprocess import call
from mush import api
from mush.engine import config


# TODO: Maybe make this an auto interface like plugins.api
class CLI(object):
    """
    TODO: Get rid of all the classmethod-ness / make the entire thing
          instantiate before running
    TODO: Now that everything is in the CLI class:
          Make the thing an interface, AND make it extensible so that
          new extensions (not implemented yet) can add to the interface.
          Define plugins for those interfaces-extensions.
          Move the implementation here to a plugin.
    """

    class _command(object):
        """All CLI commands should inherit from this, for reasons."""

        _known_flags = []

        @classmethod
        def _call(cls, data_store, aliases, *args):
            raise NotImplementedError

        @classmethod
        def help(cls, *args, **kwargs):
            return cls.__doc__

        @classmethod
        def check_aliases(cls, aliases):
            if len(aliases) < 1:
                print cls.help()
                cls.fail('No aliases entered')

        @classmethod
        def check_flags(cls, flags):
            bad_flags = [f for f in flags if f not in cls._known_flags]
            if bad_flags:
                print cls.help()
                cls.fail(
                    'Unknown flag{}: {}'.format(
                        's' if len(bad_flags) > 1 else '',
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
    def _command_names(cls, python_names=False):
        cmds = []
        # Gather all the classes that inherit from _command,
        # (except for _command)
        for k, v in cls.__dict__.items():
            try:
                if issubclass(v, cls._command) and v is not cls._command:
                    name = k if python_names else k.replace('_', '-')
                    cmds.append(name)
            except TypeError:
                # The dict is full of things that aren't classes, so
                # issubclass explodes when they're passed in.
                pass
        return cmds

    @classmethod
    def run(cls, args):
        # Get rid of the cmd
        args.remove(args[0])
        data_store = None
        known_aliases = []

        if len(args) > 0 and args[0] != 'generate-config':
            failmsg = config.check()
            if failmsg:
                print failmsg
                print "Please run mush generate-config --help for more info"
                exit(1)
            data_store = api.data_store()
            known_aliases = data_store.available_aliases()

        mush_command = None
        client_command = None
        aliases = []
        flags = {}

        def quit_with_main_help(msg=None):
            print msg
            cls._dispatch("help", data_store, aliases, args, flags)
            exit(1)

        # Run Help if nothing else was passed in
        if len(args) <= 0:
            quit_with_main_help("No options given.")

        # Parse out the aliases, mush command and flags from the client
        # command / client command args
        while args:
            arg = args[0]
            args.remove(arg)

            # Grab any mush command.  Die if more than one is found.
            if arg in cls._command_names():
                if arg in known_aliases:
                    quit_with_main_help(
                        "Your alias '{0}' collides with a mush command by the "
                        "same name.  Please rename that alias".format(arg))
                if mush_command:
                    quit_with_main_help(
                        "Only one mush command is allowed at a time")
                mush_command = arg
                continue

            if arg in known_aliases:
                aliases.append(arg)
                continue

            # Parse flags
            if arg.startswith('--'):
                arg = arg.lstrip('--')
                val = arg.split('=', 1)
                arg = val[0]
                val = val[1] if len(val) == 2 else True
                flags[arg] = val
                continue

            # if we hit a non-alias, non-flag, assume it's the
            # start of the client command and stop the loop
            # We'll put the client command back in args later
            client_command = arg
            break

        if client_command and not mush_command:
            # Issue the 'call' mush command by default
            args.insert(0, client_command)
            mush_command = "call"
            print "{}".format(" ".join(args))
        elif not client_command and not mush_command:
            # If no mush command is set by this point, then no previous rule
            # to set one applied, and a mush command was not provided.
            # Call help for the user.
            args, flags, mush_command = [], {}, "help"

        cls._dispatch(mush_command, data_store, aliases, args, flags)

    @classmethod
    def _dispatch(cls, cmd, data_store, aliases, args, flags):
        """Processes command arguments and returns the proper function"""

        # replace dashes with underscores (to support names with - in them)
        cmd = cmd.replace('-', '_')

        # Only allow calls to _command objects
        command = getattr(cls, cmd)

        if cls._command in command.__mro__ and command.__name__ != '_command':

            if flags.get('help'):
                print command.help(data_store, aliases, args, flags)
                exit(0)

            if command._known_flags:
                command.check_flags(flags)
            return command._call(data_store, aliases, args, flags)

    class help(_command):
        """ Dynamically generates help based on the help() functions
        defined in each _command based class. By default, the help() methods
        return the docstring of the command class...which is why you're seeing
        this message right now. Who calls 'help --help' anyway?!"""

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            """TODO: Maybe use textwrapper to clean this up?"""
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
            cmds.remove('help')  # Don't print help's help :)
            for name in cmds:
                helplines.append(
                    "{0}{1}".format(spacer, name.replace('_', '-')))
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

        <alias(es)>:    Requires at least one alias.
        --exportable    Display the environment vars such that you can copy
                        them and paste them as a bash command.
        --table         Display the environment vars in a pretty table.
        --config-format Display the environment vars in config section format
                        (for easy copy-paste into a config file)
        --show-blanks   Also display keys that have no configured value
                        (By default, those keys are not show)
        --keys-only     Only display keys
        --detail=<keys> Display only the keys specififed, and their values
        """
        _known_flags = [
            'show-blanks', 'detail', 'keys-only', 'exportable', 'table',
            'config-format']

        @classmethod
        def target_keys(cls, flags, env_vars):
            """ Builds the list of keys that wil be used by the
            print/formatting functions"""

            if not flags.get('show-blanks'):
                env_vars = OrderedDict(
                    (k, v) for k, v in env_vars.iteritems() if v)

            if flags.get('detail'):
                keys = flags.get('detail').split(',')
                env_vars = {k: v for k, v in env_vars.items() if k in keys}

            if flags.get('keys-only'):
                env_vars = {k: '' for k in env_vars.keys()}

            return env_vars

        @classmethod
        def exportable(cls, alias, env_vars):
            print "\n", "#", alias.upper()
            for k, v in env_vars.iteritems():
                print "export {}={}".format(k, v)

        @classmethod
        def config_format(cls, alias, env_vars):
            print "\n", "[{}]".format(alias)
            for k, v in env_vars.iteritems():
                print "{}={}".format(k, v)

        @classmethod
        def plaintext_list(cls, alias, env_vars):
            print "-" * 30
            print alias.upper()
            for k, v in env_vars.iteritems():
                print k, v

        @classmethod
        def table(cls, alias, env_vars):
            p = prettytable.PrettyTable(
                field_names=["Environment Variable", "Value"])
            [p.add_row((k, v, )) for k, v in env_vars.iteritems()]
            print "\n", alias.upper()
            print p

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            cls.check_aliases(aliases)
            for alias in aliases:
                env_vars = cls.target_keys(
                    flags, data_store.environment_variables(alias))

                # TODO: Make this call pluggable so that more print options
                #       can be added later.
                if flags.get('exportable'):
                    cls.exportable(alias, env_vars)

                elif flags.get('table'):
                    cls.table(alias, env_vars)

                elif flags.get('config-format'):
                    cls.config_format(alias, env_vars)

                else:
                    cls.plaintext_list(alias, env_vars)

    class persist(_command):
        """Spawn a new shell with all the environment variables set for
        the given user/alias.

        <alias>:        Requires one alias.
        --plugin <plugin>:
                        Override configured persist-shell plugin keyname.
        --shell-override <cmd>:
                        Ignore any installed plugins and try to run this
                        command directly via a subprocess call.
                        (Useful for one-off uses that you don't use often
                        enough to justify writing a plugin)
        """
        _known_flags = ['shell-override', 'plugin']

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            cls.check_aliases(aliases)

            for alias in aliases:
                env = os.environ.copy()
                env.update(data_store.environment_variables(alias))
                if flags.get('shell-override'):
                    call(flags.get('shell-override'), env=env)
                    continue
                plugin_keyname = flags.get('plugin') or config._config.get(
                    "default_plugins", "persist_shell")
                api.persist_shell(keyname=plugin_keyname).persist(
                    env, alias=alias)

    class call(_command):
        """Calls client command once for every alias listed

        Note: This is the default command called, you don't need to specify
        'call', you can just run 'mush <alias(es)> <client command>

        <alias(es)>:    Requires at least one alias.
        --no-stderr:    Pipes the stderr output from the client command
                        to the system's version of /dev/null
        --show-alias:   Prints the alias used before making the client call.
                        Useful when making calls to multiple aliases.
        """
        _known_flags = ['show-alias', 'no-stderr']

        @classmethod
        def _dispatch_to_shell(cls, cmd, data_store, alias, args, flags):
            stderr_out = \
                open(os.devnull, 'w') if flags.get('no-stderr') else sys.stderr
            env = os.environ.copy()
            user_env = data_store.environment_variables(alias)
            env.update(user_env)
            cmd = "{} {}".format(cmd, " ".join(args))
            call(
                cmd, stdout=sys.stdout, stderr=stderr_out, shell=True, env=env)

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

    class generate_config(_command):
        """
        Generates a configuration file based on available plugins.
        Each plugin will define a section with default key/value pairs.
        the [default_plugins] section is where you'll decide what plugins
        you want to use. Make sure to set only one item per line in the
        [default_plugins] section.

        Copy this into a file named 'config' in ~/.mush:
        """

        @classmethod
        def _call(cls, data_store, aliases, args, flags):
            from mush.plugins.interfaces import registry

            print cls.__doc__
            print '#BEGIN CONFIG'
            print "[default_plugins]"
            print "# Choose one default plugin per interface"
            for interface in registry.interfaces():
                interface_name = interface.__interface__
                plugins = ", ".join(
                    [p for p in registry.plugins(interface_name)])
                print "{}={}".format(interface_name, plugins)

            print ''
            for interface in registry.plugins().keys():
                keynames = registry.plugins(interface)
                for keyname in keynames:
                    plugin = registry.plugin(interface, keyname)
                    if plugin.__config_defaults__:
                        print "[{}.{}]".format(interface, keyname)
                        for k, v in plugin.__config_defaults__.items():
                            print "{}={}".format(k, v)
                        print ''
            print '#END CONFIG'


def entry_point():
    CLI.run(sys.argv)
