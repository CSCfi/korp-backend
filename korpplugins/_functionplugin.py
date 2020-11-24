
"""
Module korpplugins._functionplugin

Module containing code for function plugins to be called at mount points

All callable objects (typically functions) whose names begin with a lower-case
letter in a plugin module are considered as function plugins to the mount point
of the function name.

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


# Import _commondefs instead of import names from it, so that assigning to
# _commondefs.var modifies the value visible to other modules
from . import _commondefs


def call(mount_point, *args, **kwargs):
    """Call the plugins in mount_point, discarding return values

    Call the plugins in mount_point with args and kwargs in sequence,
    discarding return values.
    """
    for func in _commondefs._plugin_funcs.get(mount_point, []):
        func(*args, **kwargs)


def call_collect(mount_point, *args, **kwargs):
    """Call the plugins in mount_point, collecting return values to a list

    Call the plugins in mount_point with args and kwargs in sequence,
    collect their return values to a list and return it.
    """
    result = []
    for func in _commondefs._plugin_funcs.get(mount_point, []):
        result.append(func(*args, **kwargs))
    return result


def call_chain(mount_point, arg1, *args, **kwargs):
    """Call the plugins in mount_point, passing return value to the following

    Return the value of arg1 as passed through the plugins in
    mount_point, with the return value of the preceding plugin
    function as the arg1 value of the following one. *args and
    **kwargs are passed to each function as they are.
    """
    for func in _commondefs._plugin_funcs.get(mount_point, []):
        arg1 = func(arg1, *args, **kwargs)
    return arg1
