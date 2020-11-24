
"""
Module korpplugins._pluginloader

Module containing the korpplugins plugin loading function

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


import importlib
import sys


from korpplugins import Blueprint

# Import _commondefs instead of import names from it, so that assigning to
# _commondefs.var modifies the value visible to other modules
from . import _commondefs


def load(app, plugin_list, main_handler=None, extra_decorators=[]):
    """Load the plugins in the modules listed in plugin_list.

    Load the plugins in the modules listed in plugin_list by importing
    the modules within this package. app is the Flask application, and
    main_handler and extra_decorators as the decorators for endpoints.
    """
    # global _plugin_funcs, _router, _endpoint_decorators
    _commondefs._endpoint_decorators = dict(
        (decor.__name__, decor) for decor in extra_decorators)
    if main_handler is not None:
        _commondefs._endpoint_decorators["main_handler"] = main_handler
    for plugin in plugin_list:
        # We could implement a more elaborate or configurable plugin
        # discovery procedure if needed
        module = importlib.import_module(
            __name__.rpartition(".")[0] + "." + plugin)
        for name in dir(module):
            attr = getattr(module, name)
            if name[0].islower() and callable(attr):
                if attr not in _commondefs._plugin_funcs["ENDPOINT"]:
                    _commondefs._plugin_funcs[name].append(attr)
    Blueprint.register_all(app)
