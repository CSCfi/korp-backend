
"""
korpplugins.test3

Korp test plugin: non-JSON endpoint.
"""


import korppluginlib


PLUGIN_INFO = {
    "name": "korppluginlib test plugin 3 (non-JSON endpoint /text)",
    "version": "0.1",
    "date": "2021-01-07",
}


plugin = korppluginlib.KorpEndpointPlugin()


@plugin.route("/text", extra_decorators=["use_custom_headers"])
def text(args):
    """Return the arguments as text/plain

    If args contains "filename", add header "Content-Disposition:
    attachment" with the given filename.
    """
    result = {}
    result["content"] = "\n".join(arg + "=" + repr(args[arg]) for arg in args)
    result["mimetype"] = "text/plain"
    if "filename" in args:
        result["headers"] = [
            ("Content-Disposition",
             "attachment; filename=\"" + args["filename"] + "\"")]
    yield result
