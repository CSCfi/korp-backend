
"""
korpplugins.test2

Korp test plugin for an object-based plugin proposal: a result wrapper as a
stand-alone module.
"""


import traceback

import korpplugins


class Test2(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d, *rest):
        return {"wrap2": d}


class Test3(korpplugins.KorpFunctionPlugin):

    """Print the arguments at all plugin mount points"""

    def enter_handler(self, args, starttime, *rest):
        print("enter_handler", args, starttime, *rest)

    def exit_handler(self, endtime, elapsed, *rest):
        print("exit_handler", endtime, elapsed, *rest)

    def error(self, error, exc, *rest):
        print("error", error, traceback.format_exception(*exc))

    def filter_args(self, args, *rest):
        print("filter_args", args, *rest)

    def filter_result(self, result, *rest):
        print("filter_result", result, *rest)

    def filter_cqp_input(self, cmd, *rest):
        print("filter_cqp_input", cmd, *rest)

    def filter_cqp_output(self, output, *rest):
        print("filter_cqp_output", output, *rest)

    def filter_sql(self, sql, *rest):
        print("filter_sql", sql, *rest)
