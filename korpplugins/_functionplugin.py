
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

from flask import request as flask_request

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
            # List of subclasses
            cls._subclasses = []
        else:
            # This executes in subclasses
            # Create class instance
            cls._subclasses.append(cls)
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

    pass


class KorpFunctionPluginCaller:

    """Class for calling plugin functions at named mount points.

    This class should be instantiated once for each Flask request. The
    call methods take care of passing the actual request object to the
    plugin functions, so that it need not be specified at every call.
    """

    # Instances of this class: dict[request object id,
    # KorpFunctionPluginCaller]
    _instances = {}

    def __init__(self, request=None):
        """Initialize a KorpFunctionPluginCaller with the given request.

        If request is None, use the object for the global request proxy.
        """
        self._request = self._get_request_obj(request)
        self._instances[id(self._request)] = self

    @staticmethod
    def _get_request_obj(request=None):
        """Return the actual non-proxy Request object for request.

        If request is None, get the object for the global request proxy.
        """
        request = request or flask_request
        try:
            return request._get_current_object()
        except AttributeError:
            return request

    @classmethod
    def get_instance(cls, request=None):
        """Get the class instance for request.

        If request is None, get the instance for the global request proxy.
        """
        request_obj = cls._get_request_obj(request)
        return cls._instances[id(request_obj)]

    def cleanup(self):
        """Clean up when this KorpFunctionPluginCaller is no longer used."""
        # Remove self from _instances
        del self._instances[id(self._request)]

    def call(self, mount_point, *args, **kwargs):
        """Call the plugins in mount_point, discarding return values

        Call the plugins in mount_point with args and kwargs in sequence,
        discarding return values.
        """
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            func(*args, self._request, **kwargs)

    def call_collect(self, mount_point, *args, **kwargs):
        """Call the plugins in mount_point, collecting return values to a list

        Call the plugins in mount_point with args and kwargs in sequence,
        collect their return values to a list and return it. Return values
        None are ignored.
        """
        result = []
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            retval = func(*args, self._request, **kwargs)
            if retval is not None:
                result.append(retval)
        return result

    def call_chain(self, mount_point, arg1, *args, **kwargs):
        """Call the plugins in mount_point, passing return value to the next

        Return the value of arg1 as passed through the plugins in
        mount_point, with the return value of the preceding plugin
        function as the arg1 value of the following one, unless it is
        None, in which case arg1 is kept as is. *args and **kwargs are
        passed to each function as they are.
        """
        for func in KorpFunctionPlugin._plugin_funcs.get(mount_point, []):
            retval = func(arg1, *args, self._request, **kwargs)
            if retval is not None:
                arg1 = retval
        return arg1

    @classmethod
    def call_for_request(cls, mount_point, *args, request=None, **kwargs):
        """Call the plugins in mount_point for request.

        If request is None, use the global request proxy.
        """
        cls.get_instance(request).call(mount_point, *args, **kwargs)

    @classmethod
    def call_collect_for_request(cls, mount_point, *args, request=None,
                                 **kwargs):
        """Call the plugins in mount_point for request, collecting to a list.

        If request is None, use the global request proxy.
        """
        return cls.get_instance(request).call_collect(
            mount_point, *args, **kwargs)

    @classmethod
    def call_chain_for_request(cls, mount_point, arg1, *args, request=None,
                               **kwargs):
        """Call the plugins in mount_point for request, passing return value

        If request is None, use the global request proxy.
        """
        return cls.get_instance(request).call_chain(
            mount_point, arg1, *args, **kwargs)
