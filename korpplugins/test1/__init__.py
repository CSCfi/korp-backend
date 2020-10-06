
"""
korpplugins.test1

Korp test plugin for a Blueprint- and function-based plugin proposal:
endpoint /test and a result wrapper in a package with a separate
configuration module.
"""


from korpplugins import Blueprint

try:
    from . import config as pluginconf
except ImportError:
    class pluginconf:
        ARGS_NAME = "args_default"
        WRAP_NAME = "wrap_default"


test_plugin = Blueprint("test_plugin", __name__)


@test_plugin.route("/test", extra_decorators=["test_decor"])
def test(args):
    """Yield arguments wrapped in ARGS_NAME."""
    yield {pluginconf.ARGS_NAME: args}


def filter_result(d, request, app):
    """Wrap the result dictionary in WRAP_NAME and add "endpoint"."""
    return {"endpoint": request.endpoint,
            pluginconf.WRAP_NAME: d}
