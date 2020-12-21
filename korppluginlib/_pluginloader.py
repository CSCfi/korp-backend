
"""
Module korppluginlib._pluginloader

Module containing the korppluginlib plugin loading function

This module is intended to be internal to the package korppluginlib; the names
intended to be visible outside the package are imported at the package level.
"""


import importlib
import sys

from collections import OrderedDict
from types import SimpleNamespace

from ._configutil import pluginlibconf, add_plugin_config, plugin_configs
from ._endpointplugin import Blueprint
from ._util import print_verbose, print_verbose_delayed


# The attributes of app_globals allows accessing the values of global
# application variables (and possibly functions) passed to load(), typically at
# least "app" and "mysql". Values to app_globals are added in load(), but it is
# initialized here, so that its value is correct when it is imported at the
# package level.
app_globals = SimpleNamespace()

# An ordered dictionary of loaded plugins: keys are plugin names, values dicts
# with the key "module" (the plugin module) and any keys from the PLUGIN_INFO
# dictionary of the plugin module in question, typically "name", "version" and
# "date". The dictionary is ordered by the order in which the plugins have been
# loaded.
loaded_plugins = OrderedDict()


def load(app, plugin_list, decorators=None, app_globals=None):
    """Load the plugins in the modules listed in plugin_list.

    Load the plugins in the modules listed in plugin_list by importing
    the modules within this package. app is the Flask application, and
    decorators are the (globally available) decorators for endpoints.
    (decorators must contain main_handler.) app_globals is a
    dictionary of global application variables to be made available as
    attributes of the module global app_globals.

    The items in plugin list may be either strings (plugin names) or
    pairs (plugin name, config) where config is a dictionary- or
    namespace-like object containing values for configuration
    variables of the module. The values defined here override those in
    the possible config submodule of the plugin.
    """
    global loaded_plugins
    if not decorators or not any(decor.__name__ == "main_handler"
                                 for decor in decorators):
        raise ValueError("decorators must contain main_handler")
    Blueprint.add_endpoint_decorators(decorators)
    app_globals = app_globals or {}
    global_app_globals = globals()["app_globals"]
    for name, val in app_globals.items():
        setattr(global_app_globals, name, val)
    saved_sys_path = sys.path
    sys.path.extend(pluginlibconf.SEARCH_PATH)
    for plugin in plugin_list:
        # Add possible configuration
        if isinstance(plugin, tuple) and len(plugin) > 1:
            add_plugin_config(plugin[0], plugin[1])
            plugin = plugin[0]
        try:
            module = _find_plugin(plugin)
            # Add plugin information to loaded_plugins
            loaded_plugins[plugin] = {"module": module}
            try:
                loaded_plugins[plugin].update(module.PLUGIN_INFO)
            except AttributeError as e:
                pass
            load_msg = ("Loaded Korp plugin \"" + plugin + "\" ("
                        + module.__name__ + ")")
            if pluginlibconf.LOAD_VERBOSITY > 0:
                descr = ""
                for key, fmt in [
                    ("name", "{val}"),
                    ("version", "version {val}"),
                    ("date", "{val}"),
                ]:
                    val = loaded_plugins[plugin].get(key)
                    if val:
                        descr += (", " if descr else "") + fmt.format(val=val)
                if descr:
                    load_msg += ": " + descr
            if plugin in plugin_configs:
                print_verbose(2, "  configuration:", plugin_configs[plugin])
            print_verbose(1, load_msg, immediate=True)
            # Print the verbose messages collected when loading the plugin
            # module
            print_verbose_delayed()
        except ModuleNotFoundError as e:
            if pluginlibconf.HANDLE_NOT_FOUND == "ignore":
                continue
            msg_base = "Plugin \"" + plugin + "\" not found:"
            if pluginlibconf.HANDLE_NOT_FOUND == "warn":
                print("Warning:", msg_base, e, file=sys.stderr)
            else:
                print(msg_base, file=sys.stderr)
                raise
    sys.path = saved_sys_path
    Blueprint.register_all(app)


def _find_plugin(plugin):
    """ """
    module = None
    not_found = []
    for pkg in pluginlibconf.PACKAGES:
        module_name = pkg + "." + plugin if pkg else plugin
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            not_found.append("'" + module_name + "'")
    if len(not_found) == 1:
        not_found_str = not_found[0]
    else:
        not_found_str = ", ".join(not_found[:-1]) + " nor " + not_found[-1]
    raise ModuleNotFoundError(
        "No module named " + not_found_str + " in any of "
        + ", ".join((dir or ".") for dir in sys.path))
