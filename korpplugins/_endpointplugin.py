
"""
Module korpplugins._endpointplugin

Module containing code for WSGI endpoint plugins

In plugin modules, functions decorated with the route method of an instance of
korpplugins.Blueprint define new WSGI endpoints.

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


import functools

import flask

# Import _commondefs instead of import names from it, so that assigning to
# _commondefs.var modifies the value visible to other modules
from . import _commondefs

from ._util import print_verbose


class Blueprint(flask.Blueprint):

    """Blueprint keeping track of instances and modifying route() method"""

    # Class instances
    _instances = set()

    def route(self, rule, *, extra_decorators=None, **options):
        """Add main_handler and possible optional decorators specified in
        extra_decorators to endpoints, and default to methods=["GET", "POST"].
        """
        # global _plugin_funcs, _endpoint_decorators
        extra_decorators = extra_decorators or []
        self._instances.add(self)
        if "methods" not in options:
            options["methods"] = ["GET", "POST"]
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            # Wrap in possible extra decorators and main_handler
            for decorator_name in extra_decorators + ["main_handler"]:
                if decorator_name in _commondefs._endpoint_decorators:
                    wrapper = functools.update_wrapper(
                        _commondefs._endpoint_decorators[decorator_name](wrapper), func)
            wrapped_func = functools.update_wrapper(
                super(Blueprint, self).route(rule, **options)(wrapper), func)
            print_verbose(
                2, "  route \"" + rule + "\": endpoint " + func.__qualname__)
            return wrapped_func
        return decorator

    @classmethod
    def register_all(cls, app):
        """Register all Blueprint instances with the Flask application app."""
        for bp in cls._instances:
            app.register_blueprint(bp)
