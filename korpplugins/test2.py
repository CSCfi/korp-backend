
"""
korpplugins.test2

Korp test plugin for an object-based plugin proposal: a result wrapper as a
stand-alone module.
"""


import traceback

import korpplugins


PLUGIN_INFO = {
    "name": "korpplugins test plugin 2",
    "version": "0.1",
    "date": "2020-12-10",
}


class Test2(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d, request):
        return {"wrap2": d}


class Test3(korpplugins.KorpFunctionPlugin):

    """Print the arguments at all plugin mount points"""

    def enter_handler(self, args, starttime, request):
        print("enter_handler", args, starttime, request)
        print("app_globals:", korpplugins.app_globals)

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


class Test4a(korpplugins.KorpFunctionPlugin):

    """A function plugin that applies only to the "info" endpoint."""

    @classmethod
    def applies_to(cls, request_obj):
        return request_obj.endpoint == 'info'

    def enter_handler(self, args, starttime, request):
        print("enter_handler, info only")

    def filter_result(self, result, request):
        return {'info': result}


class Test4b(korpplugins.KorpFunctionPlugin):

    """A function plugin that applies only to all but the "info" endpoint."""

    @classmethod
    def applies_to(cls, request_obj):
        return request_obj.endpoint != 'info'

    def enter_handler(self, args, starttime, request):
        print("enter_handler, not info")
