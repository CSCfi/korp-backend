
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


class Test1a:

    @korpplugins.endpoint("/test", "test_decor")
    def test(self, args, *pargs, **kwargs):
        """Yield arguments wrapped in ARGS_NAME."""
        yield {pluginconf.ARGS_NAME: args}


class Test1b(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d, request, app):
        """Wrap the result dictionary in WRAP_NAME and add "endpoint"."""
        return {"endpoint": request.endpoint,
                pluginconf.WRAP_NAME: d}
