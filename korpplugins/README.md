
# `korpplugins`: Korp backend plugin framework (API) (instance method proposal, route as a decorator)


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

A plugin implementing a new WSGI endpoint is a generator function
defined as an instance method in a subclass of
`korpplugins.KorpEndpointPlugin`. In addition to `self`, the generator
function takes a `dict` argument containing the parameters of the call
(and a variable number of positional and keyword arguments that are
not generally used), and yields the result. The route of the endpoint
and the names of possible additional decorators (currently
`prevent_timeout`) are specified via the decorator
`korpplugins.endpoint`. For example, the following defines an endpoint
for the route `/test` with the decorator `prevent_timeout` (the name
of the method itself is not significant):

    class Test1a(korpplugins.KorpEndpointPlugin):

        @korpplugins.endpoint("/test", "prevent_timeout")
        def test(self, args, *pargs, **kwargs):
            """Yield arguments wrapped in "args"."""
            yield {"args": args}

A single class can define only one endpoint but a single plugin module
can define multiple new endpoints in separate classes.

Please note that the class is instantiated only once (it is a
singleton), so the possible state stored in `self` is shared by all
invocations (Korp requests).

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

- You cannot currently pass options to `route`, but that could be
  implemented if the need arises.


## Plugin function called at a mount point

Mount-point plugins are defined within subclasses of
`korpplugins.KorpFunctionPlugin` as instance methods having the name
of the mount point. The arguments and return values of a mount-point
plugin are specific to a mount point. Currently the following mount
points are in use:

- `filter_args(self, args, request, app)`: Modifies the arguments
  `dict` `args` to any endpoint (view function) and returns the
  modified value.

- `filter_result(self, result, request, app)`: Modifies the result
  `dict` `result` returned by any endpoint (view function) and returns
  the modified value.

- `filter_cqp_input(self, cqp, request, app)`: Modifies the raw CQP
  input string `cqp`, typically consisting of multiple CQP commands,
  already encoded as `bytes`, to be passed to the CQP executable, and
  returns the modified value.

- `filter_cqp_output(self, (output, error), request, app)`: Modifies
  the raw output of the CQP executable, a pair consisting of the
  standard output and standard error encoded as `bytes`, and returns
  the modified values as a pair.

- `enter_handler(self, args, starttime, request, app)`: Called near
  the beginning of a view function for an endpoint. `args` is a `dict`
  of arguments to the endpoint and `starttime` is the current time as
  seconds since the epoch as a floating point number. Does not return
  a value.

- `exit_handler(self, endtime, elapsed_time, request, app)`: Called
  just before exiting a view function for an endpoint (before yielding
  a response). `endtime` is the current time as seconds since the
  epoch as a floating point number, and `elapsed_time` is the time
  spent in the view function. Does not return a value.

For each mount point, the argument `request` is the Flask request
object containing information on the request, and `app` is the Flask
application object. For example, the endpoint name is available as
`request.endpoint`.

The `filter_*` mount points can of course return the input value as
is, without modifications, for example, when logging the input value
or a part of it.

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

For `filter_*` mount points, the value returned by the first plugin is
passed as the argument `args` or `result` to the second plugin, and
similarly for the second and third plugin and so on.

An example of a mount-point plugin function:

    class Test1b(korpplugins.KorpFunctionPlugin):

        def filter_result(self, result, request, app):
            """Wrap the result dictionary in "wrap" and add "endpoint"."""
            return {"endpoint": request.endpoint,
                    "wrap": result}
