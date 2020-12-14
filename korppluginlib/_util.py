
"""
Module korppluginlib._util

Module of utility functions and definitions

This module is intended to be internal to the package korppluginlib.
"""


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


# A list of tuples of print_verbose call arguments whose printing has been
# delayed until printing with print_verbose_delayed.
_delayed_print_verbose_args = []


def print_verbose(verbosity, *args, immediate=False):
    """Print args if plugin loading is configured to be verbose.

    Print if pluginconf.LOAD_VERBOSITY is at least verbosity. If
    immediate is True, print immediately, otherwise collect and print
    only with print_verbose_delayed.
    """
    if verbosity <= pluginconf.LOAD_VERBOSITY:
        if immediate:
            print(*args)
        else:
            _delayed_print_verbose_args.append(args)


def print_verbose_delayed(verbosity=None):
    """Actually print the delayed verbose print arguments.

    If verbosity is not None and is larger than
    pluginconf.LOAD_VERBOSITY, do not print."""
    global _delayed_print_verbose_args
    if verbosity is None or verbosity <= pluginconf.LOAD_VERBOSITY:
        for args in _delayed_print_verbose_args:
            print(*args)
    _delayed_print_verbose_args = []


def discard_print_verbose_delayed():
    "Discard collected delayed print verbose arguments."""
    global _delayed_print_verbose_args
    _delayed_print_verbose_args = []
