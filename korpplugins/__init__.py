
"""
Package korpplugins

A function- and Blueprint-based proposal for a plugin framework for Korp

In plugin modules, functions decorated with the route method of an instance of
korpplugins.Blueprint define new WSGI endpoints and all other callable objects
(typically functions) whose names begin with a lower-case letter are considered
as function plugins to the mount point of the function name.
"""


# This package initialization file only imports from package-internal modules
# the names to be visible to the importing code; the actual implementation is
# in the internal modules.


# The following names are visible to the code importing korpplugins
from ._endpointplugin import Blueprint
from ._functionplugin import call, call_collect, call_chain
from ._pluginloader import load
