
"""
Module korpplugins._util

Module of utility functions and definitions

This module is intended to be internal to the package korpplugins.
"""


# Try to import korpplugins.config as pluginconf; if not available, define
# class pluginconf with the same effect.
try:
    from . import config as pluginconf
except ImportError:
    class pluginconf:
        # When loading, print plugin module names but not function names
        LOAD_VERBOSITY = 1
        HANDLE_NOT_FOUND = "warn"


def print_verbose(verbosity, *args):
    """Print args if plugin loading is configured to be verbose."""
    if verbosity <= pluginconf.LOAD_VERBOSITY:
        print(*args)
