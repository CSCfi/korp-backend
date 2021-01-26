
"""
korpplugins.charcoder

Encode special characters in queries and decode in results

Assumes that corpora contain encoded special characters that would not
otherwise be handled correctly (because of limitations of CWB): space,
slash, lesser than, greater than. These characters are encoded in CQP
queries and decoded in query results.
"""


import re

import korppluginlib


# See config.py.template for further documentation of the configuration
# variables
pluginconf = korppluginlib.get_plugin_config(
    # Special characters encoded
    SPECIAL_CHARS = " /<>|",
    # The character for encoding the first character in SPECIAL_CHARS
    ENCODED_SPECIAL_CHAR_OFFSET = 0x7F,
    # Prefix for the encoded form of special characters
    ENCODED_SPECIAL_CHAR_PREFIX = "",
)


# The following constants and functions would logically belong to the class
# SpecialCharacterTranscoder, but they do not use its state, so defining them
# as independent functions avoids having to pass self to them.


# Special characters in CQP regular expressions that need to be escaped with a
# backslash to match literally. If they are not preceded with a backslash, they
# should not be replaced in queries.
_CQP_REGEX_SPECIAL_CHARS = "()|[].*+?{}^$"
# The character with which to replace literal backslashes escaped by another
# backslash, so that a regex metacharacter preceded by such will not be
# replaced. The literal backslashes are replaced before other replacements and
# they are restored after other replacements.
_REGEX_ESCAPE_CHAR_TMP = (pluginconf.ENCODED_SPECIAL_CHAR_PREFIX
                          + chr(pluginconf.ENCODED_SPECIAL_CHAR_OFFSET
                                + len(pluginconf.SPECIAL_CHARS)))
# Encoding and decoding mapping (list of pairs (string, replacement)) for
# special characters. Since the replacement for a regex metacharacter should
# not be a regex metacharacter, it is not preceded by a backslash.
_SPECIAL_CHAR_ENCODE_MAP = [
    (escape + c, (pluginconf.ENCODED_SPECIAL_CHAR_PREFIX
                  + chr(i + pluginconf.ENCODED_SPECIAL_CHAR_OFFSET)))
     for (i, c) in enumerate(pluginconf.SPECIAL_CHARS)
     for escape in ["\\" if c in _CQP_REGEX_SPECIAL_CHARS else ""]]
# Handle literal backslashes only if any of pluginconf.SPECIAL_CHARS is a regex
# metacharacter.
if any(spch == rech for spch in pluginconf.SPECIAL_CHARS
       for rech in _CQP_REGEX_SPECIAL_CHARS):
    _SPECIAL_CHAR_ENCODE_MAP = (
        [("\\\\", _REGEX_ESCAPE_CHAR_TMP)]
        + _SPECIAL_CHAR_ENCODE_MAP
        + [(_REGEX_ESCAPE_CHAR_TMP, "\\\\")])
# When decoding, we need not take into account regex metacharacter escaping
_SPECIAL_CHAR_DECODE_MAP = [(repl[-1], c[-1])
                            for (c, repl) in _SPECIAL_CHAR_ENCODE_MAP
                            if c != "\\\\" and repl != "\\\\"]


def _replace_substrings(s, mapping):
    """Replace substrings in s according to mapping (a sequence of
    pairs (string, replacement): replace each string with the
    corresponding replacement.
    """
    for (s1, repl) in mapping:
        s = s.replace(s1, repl)
    return s


def _encode_special_chars(s):
    """Encode the special characters in s."""
    return _replace_substrings(s, _SPECIAL_CHAR_ENCODE_MAP)


def _decode_special_chars(s):
    """Decode the encoded special characters in s."""
    return _replace_substrings(s, _SPECIAL_CHAR_DECODE_MAP)


def _encode_special_chars_in_query(cqp):
    """Encode the special characters in the double-quoted substrings
    of the CQP query cqp.
    """
    # Allow empty strings within double quotes, so that the regexp
    # does not match from an ending double quote of a quoted empty
    # string to the next double quote.
    return re.sub(r'("(?:[^\\"]|\\.)*")',
                  lambda mo: _encode_special_chars(mo.group(0)), cqp)


def _encode_special_chars_in_queries(cqp_list):
    """Encode the special characters in the double-quoted substrings
    of the list of CQP queryies cqp_list.
    """
    return [_encode_special_chars_in_query(cqp) for cqp in cqp_list]


class SpecialCharacterTranscoder(korppluginlib.KorpCallbackPlugin):

    def filter_args(self, args, request):
        """Encode special characters in CQP queries"""
        return self._transcode_strings(
            args, _encode_special_chars_in_query, argname_prefix='cqp')

    def filter_result(self, result, *rest):
        """Decode special characters in result"""
        return self._transcode_strings(result, _decode_special_chars)

    def _transcode_strings(self, obj, transfunc, argname_prefix=None):
        """Return obj with strings transcoded using transfunc

        Transcode strings and recursively string values in a dict or
        list (dict keys are not transcoded); all other types of
        objects are kept intact. If argname_prefix is not None and obj
        is a dict, transcode only the values of keys beginning with
        argname_prefix.
        """
        if isinstance(obj, str):
            return transfunc(obj)
        # dict
        try:
            for key, val in obj.items():
                if argname_prefix is None or key.startswith(argname_prefix):
                    obj[key] = self._transcode_strings(val, transfunc)
            return obj
        except AttributeError:
            pass
        # list
        try:
            result = []
            for val in obj:
                result.append(self._transcode_strings(val, transfunc))
            return result
        except TypeError:
            pass
        return obj
