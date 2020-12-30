
"""
korpplugins.test2

Korp test plugin for an object-based plugin proposal: a result wrapper as a
stand-alone module.
"""


import traceback

from types import SimpleNamespace

import korppluginlib


PLUGIN_INFO = {
    "name": "korppluginlib test plugin 2",
    "version": "0.1",
    "date": "2020-12-10",
}


class Test2(korppluginlib.KorpCallbackPlugin):

    def filter_result(self, d, request):
        return {"wrap2": d}


class Test3(korppluginlib.KorpCallbackPlugin):

    """Print the arguments at all plugin mount points"""

    def enter_handler(self, args, starttime, request):
        print("enter_handler", args, starttime, request)
        print("app_globals:", korppluginlib.app_globals)

    def exit_handler(self, endtime, elapsed, request):
        print("exit_handler", endtime, elapsed, request)

    def error(self, error, exc, request):
        print("error", error, traceback.format_exception(*exc))

    def filter_args(self, args, request):
        print("filter_args", args, request)

    def filter_result(self, result, request):
        print("filter_result", result, request)

    def filter_cqp_input(self, cmd, request):
        print("filter_cqp_input", cmd, request)

    def filter_cqp_output(self, output, request):
        print("filter_cqp_output", output, request)

    def filter_sql(self, sql, request):
        print("filter_sql", sql, request)


class Test4a(korppluginlib.KorpCallbackPlugin):

    """A callback plugin that applies only to the "info" endpoint."""

    @classmethod
    def applies_to(cls, request_obj):
        return request_obj.endpoint == 'info'

    def enter_handler(self, args, starttime, request):
        print("enter_handler, info only")

    def filter_result(self, result, request):
        return {'info': result}


class Test4b(korppluginlib.KorpCallbackPlugin):

    """A callback plugin that applies only to all but the "info" endpoint."""

    @classmethod
    def applies_to(cls, request_obj):
        return request_obj.endpoint != 'info'

    def enter_handler(self, args, starttime, request):
        print("enter_handler, not info")


class StateTest(korppluginlib.KorpCallbackPlugin):

    """A callback plugin keeping state (starttime) across callbacks."""

    _data = {}

    def enter_handler(self, args, starttime, request):
        self._data[request] = data = SimpleNamespace()
        data.starttime = starttime
        print("StateTest.enter_handler: starttime =", starttime)

    def exit_handler(self, endtime, elapsed, request):
        print("StateTest.exit_handler: starttime =",
              self._data[request].starttime, "endtime =", endtime)
        del self._data[request]
