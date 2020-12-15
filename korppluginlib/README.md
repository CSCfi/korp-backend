
# `korppluginlib`: Korp backend plugin framework (API) (proposal with function plugins as instance methods and Blueprint-based endpoints)


## Overview

The Korp backend supports two kinds of plugins:

1. plugins implementing new WSGI endpoints, and
2. plugin functions called at certain points (“mount points”) in
   `korp.py` when handling a request.

Plugins are defined as Python modules or subpackages within the
package `korpplugins`. (This might be relaxed so that plugin modules
or packages would not need to be within `korpplugins`.)

Both WSGI endpoint plugins and mount-point plugins can be defined in
the same plugin module.


## Configuration


### Configuring `korppluginlib`

The names of plugins (modules or subpackages) to be used are defined
in the list `PLUGINS` in `config.py` (that is, module `config`). If a
plugin module is not found, a warning is output to the standard
output.

The configuration of `korppluginlib` is in the module
`korppluginlib.config` (file `korppluginlib/config.py`). Currently,
the following configuration variables are recognized:

- `HANDLE_NOT_FOUND`: What to do when a plugin is not found:
    - `"error"`: Throw an error.
    - `"warn"` (default): Output a warning to the standard error but
      continue.
    - `"ignore"`: Silently ignore.

- `LOAD_VERBOSITY`: What `korppluginlib` outputs when loading plugins:
    - `0`: nothing
    - `1` (default): the names of loaded plugins only
    - `2`: the names of loaded plugins and the plugin functions
      handling a route or registered for a plugin mount point

Alternatively, the configuration variables may be specified in
`config.py` within the dictionary or namespace object
`PLUGINLIB_CONFIG`; for example:

    PLUGINLIB_CONFIG = dict(
        HANDLE_NOT_FOUND = "warn",
        LOAD_VERBOSITY = 1,
    )

The values specified in `config.py` override those in
`korppluginlib.config`.


### Configuring individual plugins

Values for the configuration variables of individual plugin modules or
subpackages can be specified in three places:

1. An item in the list `PLUGINS` in the Korp `config` module can be a
   pair `(`_plugin\_name_`,` _config_`)`, where _config_ may be either
   a dictionary- or namespace-like object containing configuration
   variables.

2. Korp’s `config.py` can contain a definition of the variable
   `PLUGIN_CONFIG_`_PLUGINNAME_ (where _PLUGINNAME_ is the name of the
   plugin in upper case), whose value may be either a dictionary- or
   namespace-like object with configration variables.

3. If the plugin is a subpackage (and not a single module), it can use
   separate configuration module named `config` within the package,
   consisting of configuration variables.

The value for a configuration variable is taken from the first of the
above in which it is set.

To get values from these sources, the plugin module needs to call
`korppluginlib.get_plugin_config` with default values of configuration
variables. The function returns an object containing configuration
variables with their values (an instance of `types.SimpleNamespace`).
For example:

    pluginconf = korppluginlib.get_plugin_config(
        CONFIG_VAR = "value",
    )

The configured value of `CONFIG_VAR` can be then accessed as
`pluginconf.CONFIG_VAR`. Once the plugin has been loaded, other
plugins can also access it as
`korppluginlib.plugin_configs["`_plugin_`"].CONFIG_VAR`.

Note that the value returned by `get_plugin_config` contains values
only for the keys specified in the default values given as arguments,
even if the other places for configuration variables defined
additional variables. (If `get_plugin_config` is called without
arguments, the values defined in a possible configuration module are
taken as defaults.) The default values can be specified either as
keyword arguments to `get_plugin_config` or as a single value that can
be either a dictionary- or namespace-like object. The returned value
is always a `SimpleNamespace`.


## Plugin implementing a new WSGI endpoint


### Implementing an endpoint

To implement a new WSGI endpoint, you first create an instance of
`korppluginlib.Blueprint` (a subclass of `flask.Blueprint`) as follows:

    test_plugin = korppluginlib.Blueprint("test_plugin", __name__)

The actual view function is a generator function decorated with the
`route` method of the created instance; for example:

    @test_plugin.route("/test", extra_decorators=["prevent_timeout"])
    def test(args):
        """Yield arguments wrapped in "args"."""
        yield {"args": args}

The decorator takes as its arguments the route of the endpoint, and
optionally, an iterable of the names of possible additional decorators
as the keyword argument `extra_decorators` and other options of
`route`. `extra_decorators` lists the names in the order in which they
would be specified as decorators (topmost first), that is, in the
reverse order of application. The generator function takes a single
`dict` argument containing the parameters of the call and yields the
result. For example:

A single plugin module can define multiple new endpoints.


### Defining additional endpoint decorators

By default, the endpoint decorator functions whose names can be listed
in `extra_decorators` include only `prevent_timeout`, as the endpoints
defined in this way are always decorated with `main_handler` as the
topmost decorator. However, additional decorator functions can be
defined by decorating them with
`korppluginlib.Blueprint.endpoint_decorator`; for example:

    # test_plugin is an instance of korppluginlib.Blueprint, so this is
    # equivalent to @korppluginlib.Blueprint.endpoint_decorator
    @test_plugin.endpoint_decorator
    def test_decor(generator):
        """Add to the result an extra layer with text_decor and payload."""
        @functools.wraps(generator)
        def decorated(args=None, *pargs, **kwargs):
            for x in generator(args, *pargs, **kwargs):
                yield {"test_decor": "Endpoint decorated with test_decor",
                       "payload": x}
        return decorated


### Limitations

The current implementation has at least the following limitations:

- An endpoint (the view function) defined in a plugin cannot currently
  override an existing view function for the same endpoint defined in
  `korp.py` or in a plugin loaded earlier (listed earlier in
  `config.PLUGINS`). (But if the need arises, this restriction can
  probably be lifted or relaxed, so that a viewpoint function could
  declare that it overrides another view function.)

- It is also not possible to modify the functionality of an existing
  endpoint, for example, by calling the existing view function from
  the function defined in a plugin, possibly modifying the arguments
  or the result. However, in many cases, a similar effect can be
  achieved by defining the appropriate mount-point plugin functions
  `filter_args` and `filter_result`; see below.


## Plugin function called at a mount point

Mount-point plugins are defined within subclasses of
`korppluginlib.KorpFunctionPlugin` as instance methods having the name
of the mount point. The arguments and return values of a mount-point
plugin are specific to a mount point.


### Mount points

Currently, `korp.py` contains the following mount points:

- `filter_args(self, args, request)`: Modifies the arguments
  `dict` `args` to any endpoint (view function) and returns the
  modified value.

- `filter_result(self, result, request)`: Modifies the result
  `dict` `result` returned by any endpoint (view function) and returns
  the modified value.

- `filter_cqp_input(self, cqp, request)`: Modifies the raw CQP
  input string `cqp`, typically consisting of multiple CQP commands,
  already encoded as `bytes`, to be passed to the CQP executable, and
  returns the modified value.

- `filter_cqp_output(self, (output, error), request)`: Modifies
  the raw output of the CQP executable, a pair consisting of the
  standard output and standard error encoded as `bytes`, and returns
  the modified values as a pair.

- `filter_sql(self, sql, request)`: Modifies the SQL statement
  `sql` to be passed to the MySQL/MariaDB database server and returns
  the modified value.

- `enter_handler(self, args, starttime, request)`: Called near
  the beginning of a view function for an endpoint. `args` is a `dict`
  of arguments to the endpoint and `starttime` is the current time as
  seconds since the epoch as a floating point number. Does not return
  a value.

- `exit_handler(self, endtime, elapsed_time, request)`: Called
  just before exiting a view function for an endpoint (before yielding
  a response). `endtime` is the current time as seconds since the
  epoch as a floating point number, and `elapsed_time` is the time
  spent in the view function. Does not return a value.

- `error(self, error, exc, request)`: Called after an exception
  has occurred. `error` is the `dict` to be returned in JSON as
  `ERROR`, with keys `type` and `value` (and `traceback` if
  `debug=true` had been specified), and `exc` contains exception
  information as returned by `sys.exc_info()`.

For each mount point, the argument `request` is the actual Flask
request object (not a proxy for the request) containing information on
the request. For example, the endpoint name is available as
`request.endpoint`.

For `filter_*` mount points, the value returned by a plugin is passed
as the first argument to function of the next plugin. However, if the
returned value is `None`, either explicitly or if the function has no
`return` statement with a value, the value is ignored and the argument
is passed as is to the next plugin. Thus, a plugin function that does
not modify the value need not return it.


### Mount point plugin example

An example of a mount-point plugin function to be called at mount
point `filter_result`:

    class Test1b(korppluginlib.KorpFunctionPlugin):

        def filter_result(self, result, request):
            """Wrap the result dictionary in "wrap" and add "endpoint"."""
            return {"endpoint": request.endpoint,
                    "wrap": result}


### Notes on defining a mount point plugin

Each plugin class is instantiated only once (it is a singleton), so
the possible state stored in `self` is shared by all invocations
(requests). However, see the next subsection for an approach of
keeping request-specific state across mount points.

A single plugin class can define only one plugin function for each
mount point, but a module may contain multiple classes defining plugin
functions for the same mount point.

If multiple plugins define a plugin function for a mount point, they
are called in the order in which the plugin modules are listed in
`config.PLUGINS`. If a plugin module contains multiple classes
defining a plugin function for a mount point, they are called in their
order of definition in the module.

If the plugin functions of a class should be applied only to certain
kinds of requests, for example, to a certain endpoint, the class can
override the class method `applies_to(cls, request)` to return `True`
only for requests to which the plugin is applicable. (The parameter
`request` is the actual Flask request object, not a proxy.)


### Keeping request-specific state

Request-specific data can be passed from one plugin function to
another within the same plugin class by using a `dict` attribute (or
similar) indexed by request objects (or their ids). In general, the
`enter_handler` method (the first mount point) should initialize a
space for the data for a request, and `exit_handler` (the last mount
point) should delete it. For example:

    from types import SimpleNamespace

    class StateTest(korppluginlib.KorpFunctionPlugin):

        _data = {}

        def enter_handler(self, args, starttime, request):
            self._data[request] = data = SimpleNamespace()
            data.starttime = starttime
            print("enter_handler, starttime =", starttime)

        def exit_handler(self, endtime, elapsed, request):
            print("exit_handler, starttime =", self._data[request].starttime,
                  "endtime =", endtime)
            del self._data[request]

This works in part because the `request` argument of the plugin
functions is the actual Flask request object, not the global proxy.


### Defining mount points in plugins

In addition to the mount points in `korp.py` listed above, you can
define mount points in plugins simply by calling them. For example, a
logging plugin could implement a mount point function `log` that could
be called from other plugins, both function and endpoint plugins.

Given the Flask request object (or the global request proxy)
`request`, plugins at mount point `mount_point` can be called as
follows, with `*args` and `**kwargs` as the positional and keyword
arguments and discarding the return value:

    korppluginlib.KorpFunctionPluginCaller.call_for_request(
        "mount_point", *args, request, **kwargs)

or, equivalently, getting a caller for a request and calling its
instance method (typically when the same function or method contains
several mount point plugin calls):

    plugin_caller = korppluginlib.KorpFunctionPluginCaller.get_instance(request)
    plugin_caller.call("mount_point", *args, **kwargs)

If `request` is omitted or `None`, the request object referred to by
the global request proxy is used.

Plugin functions for such additional mount points are defined in the
same way as for those in `korp.py`. The signature corresponding to the
above calls is

    mount_point(self, *args, request, **kwargs)

(where `*args` should be expanded to the actual positional arguments).
All mount point functions need to have request as the last positional
argument.

Three types of call methods are available in KorpFunctionPluginCaller:

- `call_for_request` (and instance method `call`): Call the plugin
  functions and discard their values.
- `call_chain_for_request` (and `call_chain`): Call the plugin
  functions and pass the return value as the first argument of the
  next function, and return the value returned by the last function.
- `call_collect_for_request` (and `call_collect`): Call the plugin
  functions, collect their return values to a list and finally return
  the list.

Only the first two are currently used in `korp.py`.


## Accessing main application module global variables in plugins

The values of selected global variables in the main application module
`korp.py` are available to plugin modules in the attributes of
`korppluginlib.app_globals`. The variables currently available are
`app`, `mysql` and `KORP_VERSION`, which can be accessed as
`korppluginlib.app_globals.`_name_. In this way, for example, a
plugin can access the Korp MySQL database.


## Plugin information

A plugin module or package may define `dict` `PLUGIN_INFO` containing
pieces of information on the plugin. The values of keys `"name"`,
`"version"` and `"date"` are shown in the plugin load message if
defined (and if `LOAD_VERBOSITY` is at least 1), but others can be
freely added as needed. For example:

    PLUGIN_INFO = {
        "name": "korppluginlib test plugin 1",
        "version": "0.1",
        "date": "2020-12-10",
    }

The information on loaded plugins is accessible in the variable
`korppluginlib.loaded_plugins`. Its value is an `OrderedDict` whose keys
are plugin names and values are `dict`s with the value of the key
`"module"` containing the plugin module object and the rest taken from
the `PLUGIN_INFO` defined in the plugin. The values of
`loaded_plugins` are in the order in which the plugins have been
loaded.
