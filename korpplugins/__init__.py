
"""
Package korpplugins

A class-based proposal for a plugin framework for the Korp backend (WSGI
endpoints marked by a decorator)

The classes are mostly for encapsulation: although the plugin functions are
instance methods, the instances are singletons.

Registering plugin functions (for KorpFunctionPlugin subclasses) is handled in
the metaclass, adapted from or inspired by
http://martyalchin.com/2008/jan/10/simple-plugin-framework/, whereas WSGI
endpoint methods (in KorpEndpointPlugin subclasses) are decorated for Flask
with the decorator "endpoint".
"""


import functools
import importlib
import sys

from collections import defaultdict

try:
    from . import config as pluginconf
except ImportError:
    class pluginconf:
        # When loading, print plugin module names but not function names
        LOAD_VERBOSITY = 1
        HANDLE_NOT_FOUND = "warn"


def _print_verbose(verbosity, *args):
    """Print args if plugin loading is configured to be verbose."""
    if verbosity <= pluginconf.LOAD_VERBOSITY:
        print(*args)


class Singleton(type):

    """A metaclass for singleton classes

    https://stackoverflow.com/a/6798042
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


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
        _print_verbose(
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
                    _print_verbose(2, ("  mount point \"" + name
                                       + "\": function " + attr.__qualname__))


class KorpFunctionPlugin(metaclass=KorpFunctionPluginMetaclass):

    """Actual function plugin classes are subclasses of this class, with
    plugin functions as instance methods. All methods whose names begin
    with a lowercase letter are treated as plugin functions for the
    plugin mount point of the method name.
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
    endpoint.init_decorators(
        router, main_handler,
        dict((decor.__name__, decor) for decor in extra_decorators))
    for plugin in plugin_list:
        _print_verbose(1, "Loading Korp plugin \"" + plugin + "\"")
        # We could implement a more elaborate or configurable plugin
        # discovery procedure if needed
        try:
            module = importlib.import_module(__name__ + '.' + plugin)
        except ModuleNotFoundError as e:
            if pluginconf.HANDLE_NOT_FOUND == "ignore":
                continue
            msg_base = "Plugin \"" + plugin + "\" not found:"
            if pluginconf.HANDLE_NOT_FOUND == "warn":
                print("Warning:", msg_base, e, file=sys.stderr)
            else:
                print(msg_base, file=sys.stderr)
                raise
