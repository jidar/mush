# mush
A helpful multi-utility cli that takes care of a lot of the configuration needed to use the various openstack clients.

## The basic idea

Working with the openstack command line utilities can be a little frustrating at times, especially if you routinely have to use several different combinations of users and environment-specific configuration for different deployments.

I moved all my user and environment stuff into a central data file (by default a .csv file, but there is support for other options), stored as specific combinations of environment variables and values with an alias.  Mush then gives you a cli that lets you choose which set to export before making a call to any of the external clients.  Mush doesn't care about what you're setting in the environment, and it doesn't care about the syntax of whatever client you may be using.  It just sets the env on a subprocess call to the command you specifiy, like this:

Given the following data:

	alias             : example
	OS_AUTH_URL       : https://192.168.0.1:5000
	OS_TENANT_NAME    : 12345
	OS_USERNAME       : myuser
	OS_PASSWORD       : mypassword

Assuming that the python-novaclient is installed, the following command:

	mush example nova list

Would export those OS_* env vars, then execute `nova list`.

The neat thing is that it does this in the subprocess, so your shell's environment remains untouched.

## Architecture

Mush's datastore is pluggable, so you can implement a plugin that works for whatever you need.  By default, everything is stored in a csv file.

## Plugins

There are two modules and a package inside the plugins package.

###_plugins

The actual user-contributed plugins go here.  They can be as complicated as packages themselves, or individual modules.

### interfaces

This module contains classes that define the pluggable interfaces.  You can inherit from any of these classes in your
plugin and implement the interface and everything else will work like magic.  Mush's plugability is limited by the 
interfaces defined here.

### api

This is how mush interacts with the plugins.  For every class in interface, there is also a method in api that mush will call
to retrive an implemented version of that interface class.
