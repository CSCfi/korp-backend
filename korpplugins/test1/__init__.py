
"""
korpplugins.test1

Korp test plugin for an object- and Blueprint-based plugin proposal: endpoint
/test and a result wrapper in a package with a separate configuration module.
"""


import korpplugins

try:
    from . import config as pluginconf
except ImportError:
    class pluginconf:
        ARGS_NAME = "args_default"
        WRAP_NAME = "wrap_default"


test_plugin = korpplugins.Blueprint("test_plugin", __name__)


@test_plugin.route("/test", extra_decorators=["test_decor"])
def test(args):
    """Yield arguments wrapped in ARGS_NAME."""
    yield {pluginconf.ARGS_NAME: args}


class Test1b(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d, request):
        """Wrap the result dictionary in WRAP_NAME and add "endpoint"."""
        return {"endpoint": request.endpoint,
                pluginconf.WRAP_NAME: d}
