
"""
Package korpplugins

A function- and Blueprint-based proposal for a plugin framework for
Korp

In plugin modules, functions decorated with the route method of an
instance of korpplugins.Blueprint define new WSGI endpoints and all
other callable objects (typically functions) whose names begin with a
lower-case letter are considered as function plugins to the mount
point of the function name.
"""


import functools
import importlib

import flask

from collections import defaultdict


# Plugin function registry
_plugin_funcs = defaultdict(list)

# Decorator functions for WSGI endpoint functions
_endpoint_decorators = {}


def load(app, plugin_list, main_handler=None, extra_decorators=[]):
    """Load the plugins in the modules listed in plugin_list.

    Load the plugins in the modules listed in plugin_list by importing
    the modules within this package. app is the Flask application, and
    main_handler and extra_decorators as the decorators for endpoints.
    """
    global _plugin_funcs, _router, _endpoint_decorators
    _endpoint_decorators = dict(
        (decor.__name__, decor) for decor in extra_decorators)
    if main_handler is not None:
        _endpoint_decorators["main_handler"] = main_handler
    for plugin in plugin_list:
        # We could implement a more elaborate or configurable plugin
        # discovery procedure if needed
        module = importlib.import_module(__name__ + "." + plugin)
        for name in dir(module):
            attr = getattr(module, name)
            if name[0].islower() and callable(attr):
                if attr not in _plugin_funcs["ENDPOINT"]:
                    _plugin_funcs[name].append(attr)
    Blueprint.register_all(app)


class Blueprint(flask.Blueprint):

    """Blueprint keeping track of instances and modifying route() method"""

    # Class instances
    _instances = set()

    def route(self, rule, *, extra_decorators=None, **options):
        """Add main_handler and possible optional decorators specified in
        extra_decorators to endpoints, and default to methods=["GET", "POST"].
        """
        global _plugin_funcs
        self._instances.add(self)
        if "methods" not in options:
            options["methods"] = ["GET", "POST"]
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            # Wrap in possible extra decorators and main_handler
            for decorator_name in extra_decorators + ["main_handler"]:
                if decorator_name in _endpoint_decorators:
                    wrapper = functools.update_wrapper(
                        _endpoint_decorators[decorator_name](wrapper), func)
            wrapped_func = functools.update_wrapper(
                super(Blueprint, self).route(rule, **options)(wrapper), func)
            # Mark the function as ENDPOINT so that it will not be considered
            # as a basic plugin function
            _plugin_funcs["ENDPOINT"].append(wrapped_func)
            return wrapped_func
        return decorator

    @classmethod
    def register_all(cls, app):
        """Register all Blueprint instances with the Flask application app."""
        for bp in cls._instances:
            app.register_blueprint(bp)


def call(mount_point, *args, **kwargs):
    """Call the plugins in mount_point, discarding return values

    Call the plugins in mount_point with args and kwargs in sequence,
    discarding return values.
    """
    for func in _plugin_funcs.get(mount_point, []):
        func(*args, **kwargs)


def call_collect(mount_point, *args, **kwargs):
    """Call the plugins in mount_point, collecting return values to a list

    Call the plugins in mount_point with args and kwargs in sequence,
    collect their return values to a list and return it.
    """
    result = []
    for func in _plugin_funcs.get(mount_point, []):
        result.append(func(*args, **kwargs))
    return result


def call_chain(mount_point, arg1, *args, **kwargs):
    """Call the plugins in mount_point, passing return value to the following

    Return the value of arg1 as passed through the plugins in
    mount_point, with the return value of the preceding plugin
    function as the arg1 value of the following one. *args and
    **kwargs are passed to each function as they are.
    """
    for func in _plugin_funcs.get(mount_point, []):
        arg1 = func(arg1, *args, **kwargs)
    return arg1
