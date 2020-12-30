
"""
Module korppluginlib._endpointplugin

Module containing code for WSGI endpoint plugins

In plugin modules, functions decorated with the route method of an instance of
korppluginlib.Blueprint define new WSGI endpoints.

This module is intended to be internal to the package korppluginlib; the names
intended to be visible outside the package are imported at the package level.
"""


import functools

import flask

from ._util import print_verbose


class Blueprint(flask.Blueprint):

    """Blueprint keeping track of instances and modifying route() method"""

    # Class instances
    _instances = set()
    # Available endpoint decorators (name: function)
    _endpoint_decorators = {}

    def route(self, rule, *, extra_decorators=None, **options):
        """Route with rule, adding main_handler and extra_decorators.

        Add main_handler and possible optional decorators specified in
        extra_decorators to endpoints, and default to methods=["GET", "POST"].
        extra_decorators is an iterable of strings in the reverse order of
        application, that is, in the order in which they would be specified
        as decorators (topmost first).
        """
        extra_decorators = extra_decorators or []
        self._instances.add(self)
        if "methods" not in options:
            options["methods"] = ["GET", "POST"]
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            # Wrap in possible extra decorators and main_handler
            for decorator_name in reversed(["main_handler"]
                                           + list(extra_decorators)):
                if decorator_name in self._endpoint_decorators:
                    wrapper = functools.update_wrapper(
                        self._endpoint_decorators[decorator_name](wrapper),
                        func)
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

    @classmethod
    def add_endpoint_decorators(cls, decor_list):
        """Add decor_list to the available endpoint decorators."""
        cls._endpoint_decorators.update(dict(
            (decor.__name__, decor)
            for decor in decor_list if decor is not None))

    @classmethod
    def set_endpoint_decorators(cls, decor_list):
        """Set the available endpoint decorators to decor_list."""
        cls._endpoint_decorators = {}
        cls.add_endpoint_decorators(decor_list)

    @classmethod
    def endpoint_decorator(cls, func):
        """Decorator to make func available as an endpoint decorator."""
        # Effectively return func as is but add it to endpoint decorators
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        cls.add_endpoint_decorators([func])
        return wrapper
