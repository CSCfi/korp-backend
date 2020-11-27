
"""
Package korpplugins

A class- and Blueprint-based proposal for a plugin framework for the Korp
backend

The classes are mostly for encapsulation: although the plugin functions are
instance methods, the instances are singletons. Registering plugin functions
(for KorpFunctionPlugin subclasses) is handled in the metaclass, adapted from
or inspired by http://martyalchin.com/2008/jan/10/simple-plugin-framework/

WSGI endpoints are functions decorated with the route method of an instance of
korpplugins.Blueprint.
"""


# This package initialization file only imports from package-internal modules
# the names to be visible to the importing code; the actual implementation is
# in the internal modules.


# The following names are visible to the code importing korpplugins
from ._endpointplugin import Blueprint
from ._functionplugin import KorpFunctionPlugin
from ._pluginloader import load, app_globals
