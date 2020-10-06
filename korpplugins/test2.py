
"""
korpplugins.test2

Korp test plugin for a Blueprint- and function-based plugin proposal:
a result wrapper as a stand-alone module.
"""


import korpplugins


def filter_result(d, *rest):
    """Wrap the result dictionary in "wrap2"."""
    return {"wrap2": d}
