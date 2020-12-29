
# `korppluginlib`: Korp backend plugin framework (API) (proposal)


## Overview

The Korp backend supports two kinds of plugins:

1. *endpoint plugins* implementing new WSGI endpoints, and
2. *callback plugins* containing callbacks called at certain points
   (*plugin hook points*) in `korp.py` when handling a request, to
   filter data or to perform an action.

Plugins are defined as Python modules or subpackages, by default
within the package `korpplugins` (customizable via the configuration
variable `PACKAGES`; see [below](#configuring-korppluginlib)).

Both WSGI endpoint plugins and callback plugins can be defined in the
same plugin module.


## Configuration


### Configuring `korppluginlib`

The names of plugins (modules or subpackages) to be used are defined
in the list `PLUGINS` in `config.py` (that is, Korp’s top-level module
`config`). If a plugin module is not found, a warning is output to the
standard output.

The configuration of `korppluginlib` is in the module
`korppluginlib.config` (file `korppluginlib/config.py`). Currently,
the following configuration variables are recognized:

- `PACKAGES`: A list of packages which may contain plugins; default:
  `["korpplugins"]`. The packages may be namespace packages, so their
  modules may be under different directory roots. An empty string
  denotes top-level modules without packages. The packages are
  searched for a plugin in the order in which they are listed.

- `SEARCH_PATH`: A list of directories in which to search for plugins
  (the packages listed in `PACKAGES`) in addition to default ones
  (appended to `sys.path`); default: `[]`.

- `HANDLE_NOT_FOUND`: What to do when a plugin is not found:
    - `"error"`: Throw an error.
    - `"warn"` (default): Output a warning to the standard error but
      continue.
    - `"ignore"`: Silently ignore.

- `LOAD_VERBOSITY`: What `korppluginlib` outputs when loading plugins:
    - `0`: nothing
    - `1` (default): the names of loaded plugins only
    - `2`: the names of loaded plugins and their possible
      configurations, and the view functions handling a route or
      callback methods registered for a hook point

Alternatively, the configuration variables may be specified in the
top-level module `config` within the dictionary or namespace object
`PLUGINLIB_CONFIG`; for example:

    PLUGINLIB_CONFIG = dict(
        HANDLE_NOT_FOUND = "warn",
        LOAD_VERBOSITY = 1,
    )

The values specified in the top-level `config` override those in
`korppluginlib.config`.


### Configuring individual plugins

Values for the configuration variables of individual plugin modules or
subpackages can be specified in three places:

1. An item in the list `PLUGINS` in Korp’s top-level `config` module
   can be a pair `(`_plugin\_name_`,` _config_`)`, where _config_ may
   be either a dictionary- or namespace-like object containing
   configuration variables.

2. Korp’s top-level `config` module can define the variable
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


## Endpoint plugins


### Implementing a new WSGI endpoint

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
  probably be lifted or relaxed, so that a view function could declare
  that it overrides another view function.)

- It is also not possible to modify the functionality of an existing
  endpoint, for example, by calling the existing view function from
  the function defined in a plugin, possibly modifying the arguments
  or the result. However, in many cases, a similar effect can be
  achieved by defining the appropriate callback methods for hook
  points `filter_args` and `filter_result`; see
  [below](#filter-hook-points).


## Callback plugins

Callbacks to be called at specific *plugin hook points* in `korp.py`
are defined within subclasses of `korppluginlib.KorpCallbackPlugin` as
instance methods having the name of the hook point. The arguments and
return values of a callback method are specific to a hook point.

In the argument `request`, each callback method gets the actual Flask
request object (not a proxy for the request) containing information on
the request. For example, the endpoint name is available as
`request.endpoint`.

`korp.py` contains two kinds of hook points:

1. *filter hook points* call callbacks that may filter (modify) a
   value, and
2. *event hook points* call callbacks when a specific event has taken
   place.


### Filter hook points

For filter hook points, the value returned by a callback method is
passed as the first argument to the callback method defined by the
next plugin, similar to function composition or method chaining.
However, a callback for a filter hook point *need not* modify the
value: if the returned value is `None`, either explicitly or if the
method has no `return` statement with a value, the value is ignored
and the argument is passed as is to the callback method in the next
plugin. Thus, a callback method that does not modify the value need
not return it.

Filter hook points and the signatures of their callback methods are
the following:

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


### Event hook points

Callback methods for event hook points do not return a value. (A
possible return value is ignored.)

Event hook points and the signatures of their callback methods are the
following:

- `enter_handler(self, args, starttime, request)`: Called near
  the beginning of a view function for an endpoint. `args` is a `dict`
  of arguments to the endpoint and `starttime` is the current time as
  seconds since the epoch as a floating point number.

- `exit_handler(self, endtime, elapsed_time, request)`: Called
  just before exiting a view function for an endpoint (before yielding
  a response). `endtime` is the current time as seconds since the
  epoch as a floating point number, and `elapsed_time` is the time
  spent in the view function as seconds.

- `error(self, error, exc, request)`: Called after an exception
  has occurred. `error` is the `dict` to be returned in JSON as
  `ERROR`, with keys `type` and `value` (and `traceback` if
  `debug=true` had been specified), and `exc` contains exception
  information as returned by `sys.exc_info()`.


### Callback plugin example

An example of a callback plugin containing a callback method to be
called at the hook point `filter_result`:

    class Test1b(korppluginlib.KorpCallbackPlugin):

        def filter_result(self, result, request):
            """Wrap the result dictionary in "wrap" and add "endpoint"."""
            return {"endpoint": request.endpoint,
                    "wrap": result}


### Notes on implementing a callback plugin

Each plugin class is instantiated only once (it is a singleton), so
the possible state stored in `self` is shared by all invocations
(requests). However, see [the next
subsection](#keeping-request-specific-state) for an approach of
keeping request-specific state across hook points.

A single plugin class can define only one callback method for each
hook point, but a module may contain multiple classes defining
callback methods for the same hook point.

If multiple plugins define a callback method for a hook point, they
are called in the order in which the plugin modules are listed in
`config.PLUGINS`. If a plugin module contains multiple classes
defining a callback method for a hook point, they are called in the
order in which they are defined in the module.

If the callback methods of a class should be applied only to certain
kinds of requests, for example, to a certain endpoint, the class can
override the class method `applies_to(cls, request)` to return `True`
only for requests to which the plugin is applicable. (The parameter
`request` is the actual Flask request object, not a proxy.)


### Keeping request-specific state

Request-specific data can be passed from one callback method to
another within the same callback plugin class by using a `dict`
attribute (or similar) indexed by request objects (or their ids). In
general, the `enter_handler` callback method (called at the first hook
point) should initialize a space for the data for a request, and
`exit_handler` (called at the last hook point) should delete it. For
example:

    from types import SimpleNamespace

    class StateTest(korppluginlib.KorpCallbackPlugin):

        _data = {}

        def enter_handler(self, args, starttime, request):
            self._data[request] = data = SimpleNamespace()
            data.starttime = starttime
            print("enter_handler, starttime =", starttime)

        def exit_handler(self, endtime, elapsed, request):
            print("exit_handler, starttime =", self._data[request].starttime,
                  "endtime =", endtime)
            del self._data[request]

This works in part because the `request` argument of the callback
methods is the actual Flask request object, not the global proxy.


### Defining hook points in plugins

In addition to the hook points in `korp.py` listed above, you can
define hook points in plugins by invoking callbacks with the name of
the hook point by using special call methods. For example, a logging
plugin could implement a callback method `log` that could be called
from other plugins, both callback and endpoint plugins.

Given the Flask request object (or the global request proxy)
`request`, callbacks for the (event) hook point `hook_point` can be
called as follows, with `*args` and `**kwargs` as the positional and
keyword arguments and discarding the return value:

    korppluginlib.KorpCallbackPluginCaller.call_for_request(
        "hook_point", *args, request, **kwargs)

or, equivalently, getting a caller object for a request and calling
its instance method (typically when the same function or method
contains several hook points):

    plugin_caller = korppluginlib.KorpCallbackPluginCaller.get_instance(request)
    plugin_caller.call("hook_point", *args, **kwargs)

If `request` is omitted or `None`, the request object referred to by
the global request proxy is used.

Callbacks for such additional hook points are defined in the same way
as for those in `korp.py`. The signature corresponding to the above
calls is

    hook_point(self, *args, request, **kwargs)

(where `*args` should be expanded to the actual positional arguments).
All callback methods need to have request as the last positional
argument.

Three types of call methods are available in KorpCallbackPluginCaller:

- `call_for_request` (and instance method `call`): Call the callback
  methods and discard their possible return values (for event hook
  points).

- `call_chain_for_request` (and `call_chain`): Call the callback
  methods and pass the return value as the first argument of the next
  callback method, and return the value returned by the last callback
  emthod (for filter hook points).

- `call_collect_for_request` (and `call_collect`): Call the callback
  methods, collect their return values to a list and finally return
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
the `PLUGIN_INFO` defined in the plugin. The values in
`loaded_plugins` are in the order in which the plugins have been
loaded.
