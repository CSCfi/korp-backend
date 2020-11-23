
"""
Module korpplugins._endpointplugin

Module containing code for WSGI endpoint plugins

Plugins implementing WSGI endpoints are decorated for Flask with the
decorator "endpoint".

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


import functools

from ._util import print_verbose


class endpoint:

    """Decorator class for marking an instance method a WSGI endpoint."""

    # Global state initialized in the init_decorators static method
    _router = None
    _main_handler = None
    _extra_decorators = None

    def __init__(self, route, *extra_decorators):
        """Set values based on decorator arguments"""
        self._route = route
        self._endpoint_extra_decorators = extra_decorators

    def __call__(self, func):
        """Return a decorated function"""
        def wrapper(*args, **kwargs):
            # KLUDGE/FIXME: The first argument is dummy covering "self" of the
            # method to be decorated. (Why is that needed? Does this explain it
            # and provide a more correct solution:
            # https://stackoverflow.com/q/30104047)
            return func(None, *args, **kwargs)
        cls = endpoint
        for decorator_name in self._endpoint_extra_decorators:
            if decorator_name in cls._extra_decorators:
                wrapper = functools.update_wrapper(
                    cls._extra_decorators[decorator_name](wrapper), func)
        print_verbose(
            2, "  route \"" + self._route + "\": endpoint " + func.__qualname__)
        return cls._router(self._route, methods=["GET", "POST"])(
            cls._main_handler(wrapper))

    @staticmethod
    def init_decorators(router, main_handler, extra_decorators):
        """Initialize the decorators marking the endpoint method for Flask.
        This method should be called before even defining subclasses.
        """
        cls = endpoint
        cls._router = router
        cls._main_handler = main_handler
        cls._extra_decorators = extra_decorators
