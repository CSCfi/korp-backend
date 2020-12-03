
# `korpplugins`: Korp backend plugin framework (API) (proposal with function plugins as instance methods and Blueprint-based endpoints)


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

The names of plugins (modules or subpackages) to be used are defined
in the list `PLUGINS` in `config.py`. If a plugin module is not found,
a warning is output to the standard output.

The configuration of `korpplugins` is in the module
`korpplugins.config`. Currently, the following configuration variables
are recognized:

- `HANDLE_NOT_FOUND`: What to do when a plugin is not found:
    - `"error"`: Throw an error.
    - `"warn"` (default): Output a warning to the standard error but
      continue.
    - `"ignore"`: Silently ignore.

- `LOAD_VERBOSITY`: What `korpplugins` outputs when loading plugins:
    - `0`: nothing
    - `1` (default): the names of loaded plugins only
    - `2`: the names of loaded plugins and the plugin functions
      handling a route or registered for a plugin mount point

Individual plugin packages can use separate configuration modules
(customarily also named `config`) within the package.


## Plugin implementing a new WSGI endpoint

To implement a new WSGI endpoint, you first create an instance of
`korpplugins.Blueprint` (a subclass of `flask.Blueprint`) as follows:

    test_plugin = korpplugins.Blueprint("test_plugin", __name__)

The actual view function is a generator function decorated with the
`route` method of the created instance. The decorator takes as its
arguments the route of the endpoint, and optionally the names of
possible additional decorators as the keyword argument
`extra_decorators` (currently `prevent_timeout`) and other options of
`route`. The generator function takes a single `dict` argument
containing the parameters of the call and yields the result. For
example:

    @test_plugin.route("/test", extra_decorators=["prevent_timeout"])
    def test(args):
        """Yield arguments wrapped in "args"."""
        yield {"args": args}

A single plugin module can define multiple new endpoints.

Additional endpoint decorator functions (whose names can be listed in
`extra_decorators`) can be defined by decorating them with
`korpplugins.Blueprint.endpoint_decorator`; for example:

    # test_plugin is an instance of korpplugins.Blueprint, so this is
    # equivalent to @korpplugins.Blueprint.endpoint_decorator
    @test_plugin.endpoint_decorator
    def test_decor(generator):
        """Add to the result an extra layer with text_decor and payload."""
        @functools.wraps(generator)
        def decorated(args=None, *pargs, **kwargs):
            for x in generator(args, *pargs, **kwargs):
                yield {"test_decor": "Endpoint decorated with test_decor",
                       "payload": x}
        return decorated

Limitations:

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
`korpplugins.KorpFunctionPlugin` as instance methods having the name
of the mount point. The arguments and return values of a mount-point
plugin are specific to a mount point. Currently the following mount
points are in use:

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

Please note that each plugin class is instantiated only once (it is a
singleton), so the possible state stored in `self` is shared by all
invocations.

A single plugin class can define only one plugin function for each
mount point, but a module may contain multiple classes defining plugin
functions for the same mount point.

If multiple plugins define a plugin function for a mount point, they
are called in the order in which the plugin modules are listed in
`config.PLUGINS`. If a plugin module contains multiple classes
defining a plugin function for a mount point, they are called in their
order of definition in the module.

For `filter_*` mount points, the value returned by a plugin is passed
as the first argument to function of the next plugin. However, if the
returned value is `None`, either explicitly or if the function has no
`return` statement with a value, the value is ignored and the argument
is passed as is to the next plugin. Thus, a plugin function that does
not modify the value need not return it.

An example of a mount-point plugin function:

    class Test1b(korpplugins.KorpFunctionPlugin):

        def filter_result(self, result, request):
            """Wrap the result dictionary in "wrap" and add "endpoint"."""
            return {"endpoint": request.endpoint,
                    "wrap": result}


## Accessing main application module global variables in plugins

The values of selected global variables in the main application module
`korp.py` are available to plugin modules in the attributes of
`korpplugins.app_globals`. The variables currently available are
`app`, `mysql` and `KORP_VERSION`, which can be accessed as
`korpplugins.app_globals.`_name_. In this way, for example, a
plugin can access the Korp MySQL database.
