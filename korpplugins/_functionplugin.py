
"""
Module korpplugins._functionplugin

Module containing code for function plugins to be called at mount points

The classes are mostly for encapsulation: although the plugin functions are
instance methods, the instances are singletons. Registering plugin functions in
KorpFunctionPlugin subclasses is handled in the metaclass, adapted from or
inspired by http://martyalchin.com/2008/jan/10/simple-plugin-framework/ .

This module is intended to be internal to the package korpplugins; the names
intended to be visible outside the package are imported at the package level.
"""


from collections import defaultdict

from ._util import print_verbose


class Singleton(type):

    """A metaclass for singleton classes

    https://stackoverflow.com/a/6798042
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


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
            # Methods defined in the base class are not plugin functions:
            # record them here so that they can be excluded when registering
            # plugin functions in subclasses
            cls._base_methods = [name for name in attrs]
        else:
            # This executes in subclasses
            # Create class instance
            inst = cls()
            for name in dir(inst):
                attr = getattr(inst, name)
                if (name[0].islower() and callable(attr)
                        and name not in cls._base_methods):
                    cls._plugin_funcs[name].append(attr)
                    print_verbose(
                        2, ("  mount point \"" + name
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
        collect their return values to a list and return it. Return values
        None are ignored.
        """
        result = []
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            retval = func(*args, **kwargs)
            if retval is not None:
                result.append(retval)
        return result

    @staticmethod
    def call_chain(mount_point, arg1, *args, **kwargs):
        """Call the plugins in mount_point, passing return value to the next

        Return the value of arg1 as passed through the plugins in
        mount_point, with the return value of the preceding plugin
        function as the arg1 value of the following one, unless it is
        None, in which case arg1 is kept as is. *args and **kwargs are
        passed to each function as they are.
        """
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            retval = func(arg1, *args, **kwargs)
            if retval is not None:
                arg1 = retval
        return arg1
