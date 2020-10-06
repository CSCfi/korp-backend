
# `korpplugins`: Korp backend plugin framework (API) (Blueprint-based proposal)


## Overview

The Korp backend supports two kinds of plugins:

1. plugins implementing new WSGI endpoints, and
2. plugin functions called at certain points (“mount points”) in
   `korp.py` when handling a request.

Plugins are defined as Python modules or subpackages within the
package `korpplugins`. (This might be relaxed so that plugin modules
or packages would not need to be within `korpplugins`.)

The names of plugins (modules or subpackages) to be used are defined
in the list `PLUGINS` in `config.py`.

Plugin packages can use separate configuration modules (customarily
also named `config`) within the package.

Both WSGI endpoint plugins and mount-point plugins can be defined in
the same plugin module.


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

Mount-point plugins are defined as callables (usually functions)
having the name of the mount point. The arguments and return values of
a mount-point plugin are specific to a mount point. Currently the
following mount points are in use:

- `filter_args(args, request, app)`: Modifies the arguments `dict`
  `args` to any endpoint (view function) and returns the modified
  value.

- `filter_result(result, request, app)`: Modifies the result `dict`
  `result` returned by any endpoint (view function) and returns the
  modified value.

- `enter_handler(args, starttime, request, app)`: Called near the
  beginning of a view function for an endpoint. `args` is a `dict` of
  arguments to the endpoint and `starttime` is the current time as
  seconds since the epoch as a floating point number. Does not return
  a value.

- `exit_handler(endtime, elapsed_time, request, app)`: Called just
  before exiting a view function for an endpoint (before yielding a
  response). `endtime` is the current time as seconds since the epoch
  as a floating point number, and `elapsed_time` is the time spent in
  the view function. Does not return a value.

For each mount point, the argument `request` is the Flask request
object containing information on the request, and `app` is the Flask
application object. For example, the endpoint name is available as
`request.endpoint`.

If multiple plugins define a plugin function for a mount point, they
are called in the order in which the plugins are listed in
`config.PLUGINS`. For `filter_args` and `filter_result`, the value
returned by the first plugin is passed as the argument `args` or
`result` to the second plugin, and similarly for the second and third
plugin and so on.

A single plugin module can define only one plugin function for each
mount point.

An example of a mount-point plugin function:

    def filter_result(result, request, app):
        """Wrap the result dictionary in "wrap" and add "endpoint"."""
        return {"endpoint": request.endpoint,
                "wrap": result}
