
"""
korpplugins.test1

Korp test plugin for an object-based plugin proposal: endpoint /test and
a result wrapper in a package with a separate configuration module.
"""


import korpplugins

try:
    from . import config as pluginconf
except ImportError:
    class pluginconf:
        ARGS_NAME = "args_default"
        WRAP_NAME = "wrap_default"


class Test1a(korpplugins.KorpEndpointPlugin):

    # Could we have a class decorator which would get these as arguments?
    route = "/test"
    extra_decorators = ["test_decor"]

    def endpoint(self, args, *pargs, **kwargs):
        """Yield arguments wrapped in ARGS_NAME."""
        yield {pluginconf.ARGS_NAME: args}


class Test1b(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d):
        """Wrap the result dictionary in WRAP_NAME."""
        return {pluginconf.WRAP_NAME: d}
