
"""
korpplugins.test2

Korp test plugin for an object-based plugin proposal: a result wrapper as a
stand-alone module.
"""


import korpplugins


class Test2(korpplugins.KorpFunctionPlugin):

    def filter_result(self, d):
        return {"wrap2": d}
