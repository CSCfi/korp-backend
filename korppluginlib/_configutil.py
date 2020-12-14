
"""
Module korppluginlib._configutil

Module of utility functions and definitions for plugin configuration.

This module is intended to be internal to the package korppluginlib; the names
intended to be visible outside the package are imported at the package level.
"""


import importlib
import inspect

from types import SimpleNamespace

import config as korpconf


# Try to import korppluginlib.config as _pluginconf; if not available, define
# _pluginconf as a SimpleNamespace. These are used to fill in the pluginconf
# SimpleNamespace below.
try:
    from . import config as _pluginconf
except ImportError:
    _pluginconf = SimpleNamespace()


# Default configuration values, if found neither in module korppluginlib.config
# nor config
_conf_defaults = SimpleNamespace(
    # When loading, print plugin module names but not function names
    LOAD_VERBOSITY = 1,
    # Warn if a plugin is not found
    HANDLE_NOT_FOUND = "warn",
)


def _make_config(default_conf, *other_confs0):
    """Return a config object with values from default_conf or other_confs.

    The returned object is a SimpleNamespace object that has a value
    for each attribute in default_conf. The value is overridden by the
    corresponding value in the first of other_confs0 that has an
    attribute with the same name. other_confs0 are objects with
    attribute access or pairs (conf, prefix), where conf is the object
    and prefix a string to be prefixed to attributes when searching
    from conf.

    Each argument config object may be either a namespace-like object
    with attributes, in which case its __dict__ attribute is
    inspected, or a dictionary-like object with keys (and .items).
    """
    result_conf = SimpleNamespace()
    other_confs = []
    for conf in other_confs0:
        bare_conf, prefix = conf if isinstance(conf, tuple) else (conf, "")
        other_confs.append((_get_dict(bare_conf), prefix))
    for attrname, value in _get_dict(default_conf).items():
        for conf, prefix in other_confs:
            try:
                value = conf[prefix + attrname]
                break
            except KeyError:
                pass
        setattr(result_conf, attrname, value)
    return result_conf


def _get_dict(obj):
    """Return a dictionary representation of obj."""
    return obj if isinstance(obj, dict) else obj.__dict__


# An object containing configuration attribute values. Values are checked first
# from the Korp configuration (with prefix "PLUGINS_"), then in
# korppluginlib.config, then the defaults in _conf_defaults.
pluginconf = _make_config(_conf_defaults, (korpconf, "PLUGINS_"), _pluginconf)


# Plugin configuration variables, added by add_plugin_config (plugin name ->
# namespace)
_plugin_configs = {}


def add_plugin_config(plugin_name, config):
    """Add config as the configuration of plugin plugin_name.

    The values in config will override those specified as defaults in
    the plugin or in the config module of the plugin.
    """
    global _plugin_configs
    _plugin_configs[plugin_name] = (
        SimpleNamespace(**config) if isinstance(config, dict) else config)


def get_plugin_config(defaults=None, **kw_defaults):
    """Get the configuration for the calling plugin, defaulting to defaults

    Return a namespace object with configuration variables as
    attributes. The attribute names are either the names of the keyword
    arguments kw_defaults or the keys or attributes of defaults, which
    can be either a dictionary- or namespace-like object. Values are
    taken from the first of the following three in which a value is
    found: (1) plugin configuration added using add_plugin_config
    (typically in the list of plugins to load); (2) "config" module for
    the plugin (korpplugins.<plugin>.config); and (3) defaults.

    Note that if defaults is not specified or is empty and no keyword
    arguments are specified, the returned namespace object is empty,
    even if the other places for configuration had defined some
    variables.
    """
    if defaults is None:
        defaults = kw_defaults
    # Use the facilities in the module inspect to avoid having to pass __name__
    # as an argument to the function (https://stackoverflow.com/a/1095621)
    module_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    # Assume module name korpplugins.<plugin>.module[.submodule...]
    module_name_comps = module_name.split(".")
    plugin = module_name_comps[1]
    pkg = module_name_comps[0] + "." + plugin
    try:
        plugin_config_mod = importlib.import_module(pkg + ".config")
    except ImportError:
        plugin_config_mod = SimpleNamespace()
    return _make_config(defaults or {}, _plugin_configs.get(plugin, {}),
                        plugin_config_mod)
