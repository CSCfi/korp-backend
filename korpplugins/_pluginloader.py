
"""
Module korpplugins._pluginloader

Module containing the korpplugins plugin loading function

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


import importlib
import sys

from types import SimpleNamespace

from ._endpointplugin import Blueprint
from ._util import pluginconf, print_verbose


# The attributes of app_globals allows accessing the values of global
# application variables (and possibly functions) passed to load(), typically at
# least "app" and "mysql". Values to app_globals are added in load(), but it is
# initialized here, so that its value is correct when it is imported at the
# package level.
app_globals = SimpleNamespace()


def load(app, plugin_list, main_handler=None, extra_decorators=None,
         app_globals=None):
    """Load the plugins in the modules listed in plugin_list.

    Load the plugins in the modules listed in plugin_list by importing
    the modules within this package. app is the Flask application, and
    main_handler and extra_decorators as the decorators for endpoints.
    app_globals is a dictionary of global application variables to be
    made available as attributes of the module global app_globals.
    """
    Blueprint.set_endpoint_decorators(
        [main_handler] + (extra_decorators or []))
    app_globals = app_globals or {}
    global_app_globals = globals()["app_globals"]
    for name, val in app_globals.items():
        setattr(global_app_globals, name, val)
    for plugin in plugin_list:
        print_verbose(1, "Loading Korp plugin \"" + plugin + "\"")
        # We could implement a more elaborate or configurable plugin
        # discovery procedure if needed
        try:
            module = importlib.import_module(
                __name__.rpartition('.')[0] + '.' + plugin)
        except ModuleNotFoundError as e:
            if pluginconf.HANDLE_NOT_FOUND == "ignore":
                continue
            msg_base = "Plugin \"" + plugin + "\" not found:"
            if pluginconf.HANDLE_NOT_FOUND == "warn":
                print("Warning:", msg_base, e, file=sys.stderr)
            else:
                print(msg_base, file=sys.stderr)
                raise
    Blueprint.register_all(app)
