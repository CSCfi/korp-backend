
"""
Package korpplugins

A class-based proposal for a plugin framework for the Korp backend

The classes are mostly for encapsulation: although the plugin functions are
instance methods, the instances are singletons.

Registering plugin functions (for KorpFunctionPlugin subclasses) and decorating
WSGI endpoints for Flask (for KorpEndpointPlugin subclasses) are handled in
their metaclasses, adapted from or inspired by
http://martyalchin.com/2008/jan/10/simple-plugin-framework/
"""


import importlib

from collections import defaultdict


class Singleton(type):

    """A metaclass for singleton classes

    https://stackoverflow.com/a/6798042
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class KorpEndpointPluginMetaclass(Singleton):

    """This metaclass takes care of decorating appropriately the method
    "endpoint" of the plugin classes (subclasses of KorpEndpointPlugin),
    so that Flask recognizes it.
    """

    def __init__(cls, name, bases, attrs):
        if bases and cls.route and cls._router and "endpoint" in attrs:
            # Create a singleton instance and decorate it
            inst = cls()
            inst.endpoint = cls._decorate_endpoint(inst.endpoint)

    def _decorate_endpoint(cls, func):
        for decorator_name in cls.extra_decorators:
            if decorator_name in cls._extra_decorators:
                func = cls._extra_decorators[decorator_name](func)
        return cls._router(cls.route, methods=["GET", "POST"])(
            cls._main_handler(func))


class KorpEndpointPlugin(metaclass=KorpEndpointPluginMetaclass):

    """Actual WSGI endpoint plugin classes inherit from this class.
    """

    # These static variables should not be changed in subclasses
    _router = None
    _main_handler = None
    _extra_decorators = None

    # Could we have a class decorator which would get the following as
    # arguments?
    # The route string: must be overwritten by subclasses
    route = None
    # extra_decorators may contain strings corresponding to other
    # decorators, such as prevent_timeout.
    extra_decorators = []

    def endpoint(self, args, *pargs, **kwargs):
        """The method implementing a new WSGI endpoint, to be defined in
        subclasses.
        """
        pass

    @staticmethod
    def init_decorators(router, main_handler, extra_decorators):
        """Initialize the decorators marking the endpoint method for Flask.
        This method should be called before even defining subclasses,
        as the metaclass uses the values of these static variables.
        """
        cls = KorpEndpointPlugin
        cls._router = router
        cls._main_handler = main_handler
        cls._extra_decorators = extra_decorators


class KorpFunctionPluginMetaclass(Singleton):

    """This metaclass takes care of registering the plugin functions
    (methods) in the plugin classes (subclasses of
    KorpFunctionPlugin); see
    http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    """

    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, "_plugin_funcs"):
            # This executes when initializing the base class for the
            # first time
            cls._plugin_funcs = defaultdict(list)
            # Functions defined in the base class are not plugin functions but
            # caller functions: record them here so that they can be excluded
            # when registering plugin functions in subclasses
            cls._caller_funcs = [name for name in attrs]
        else:
            # This executes in subclasses
            # Create class instance
            inst = cls()
            for name in dir(inst):
                attr = getattr(inst, name)
                if (name[0].islower() and callable(attr)
                        and name not in cls._caller_funcs):
                    cls._plugin_funcs[name].append(attr)


class KorpFunctionPlugin(metaclass=KorpFunctionPluginMetaclass):

    """Actual function plugin classes are subclasses of this class, with
    plugin functions as instance methods. All methods whose names begin with a lowercase
    letter are treated as plugin functions for the plugin mount point
    of the method name.
    """

    @staticmethod
    def call(mount_point, *args, **kwargs):
        """Call the plugins in mount_point, discarding return values

        Call the plugins in mount_point with args and kwargs in sequence,
        discarding return values.
        """
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            func(*args, **kwargs)

    @staticmethod
    def call_collect(mount_point, *args, **kwargs):
        """Call the plugins in mount_point, collecting return values to a list

        Call the plugins in mount_point with args and kwargs in sequence,
        collect their return values to a list and return it.
        """
        result = []
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            result.append(func(*args, **kwargs))
        return result

    @staticmethod
    def call_chain(mount_point, arg1, *args, **kwargs):
        """Call the plugins in mount_point, passing return value to the next

        Return the value of arg1 as passed through the plugins in
        mount_point, with the return value of the preceding plugin
        function as the arg1 value of the following one. *args and
        **kwargs are passed to each function as they are.
        """
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            arg1 = func(arg1, *args, **kwargs)
        return arg1


def load(plugin_list, router=None, main_handler=None, extra_decorators=[]):
    """Load the plugins in the modules listed in plugin_list by
    importing the modules within this package, and use router,
    main_handler and extra_decorators as the decorators for Flask.
    """
    KorpEndpointPlugin.init_decorators(
        router, main_handler,
        dict((decor.__name__, decor) for decor in extra_decorators))
    for plugin in plugin_list:
        # We could implement a more elaborate or configurable plugin discovery
        # procedure if needed
        module = importlib.import_module(__name__ + '.' + plugin)
