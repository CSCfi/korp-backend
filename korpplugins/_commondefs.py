
"""
Module korpplugins._commondefs

Module containing common variable definitions for the korpplugins internal
modules. In general, the module should be imported with "from . import
_commondefs" instead of importing individual names, so that assigning to
_commondefs.var modifies the value visible to other modules.

This module is intended to be internal to the package korpplugins.
"""


from collections import defaultdict


# _endpoint_decorators is imported by the internal modules

# Decorator functions for WSGI endpoint functions
_endpoint_decorators = {}
