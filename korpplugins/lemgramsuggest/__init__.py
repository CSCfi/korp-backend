
"""
korpplugins.lemgramsuggest

A Korp plugin implementing /lemgram_suggest endpoint, to get lemgram
suggestions for autocompleting a prefix.
"""


# TODO:
# - Add docstrings and expand existing ones.
# - Add parameters affecting the result.


from flask import request

import korpplugins


# The name of the MySQL database and table prefix
DBTABLE = "lemgram_index"


plugin = korpplugins.Blueprint("lemgramsuggest_plugin", __name__)


@plugin.route("/lemgram_suggest", extra_decorators=["prevent_timeout"])
def lemgram_suggest(args):
    """Suggest lemgrams with the specified prefix.

    Suggest lemgrams beginning with the specified prefix, based on the
    database table lemgram_index. If corpus ids are specified, prefer
    lemgrams from those corpora and fill in from the rest. The result is
    sorted descending by the frequency of the lemgram.

    Arguments:
    - wf: lemgram prefix
    - corpus (optional): list of corpus ids from which to get the
      lemgrams in the first place
    - limit (default: 10): the number of lemgrams to return
    """
    wf = args.get("wf")
    corpora = args.get("corpus")
    limit = int(args.get("limit", 10))
    if corpora:
        corpora = corpora.split(',')
    result = _get_lemgrams(wf, corpora, limit)
    yield {
        "div": result,
        "count": len(result),
    }


def _get_lemgrams(wf, corpora, limit):
    app_globals = korpplugins.app_globals
    with app_globals.app.app_context():
        cursor = app_globals.mysql.connection.cursor()
        result = _query_lemgrams(cursor, wf, corpora, limit)[:limit]
    return _encode_lemgram_result(result)


def _query_lemgrams(cursor, wf, param_corpora, limit):
    result = []
    # Also collect the results in a set to filter out duplicates
    result_set = set()
    modcase = (lambda w: w.lower()) if wf.islower() else (lambda w: w)
    corpora_lists = [param_corpora]
    if param_corpora:
        corpora_lists.append([])
    # Search for lemmas in the selected corpora, lemma prefixes in
    # them, lemmas in all corpora and lemma prefixes in them, in this
    # order, only until the limit is reached.
    for corpora in corpora_lists:
        for suffpatt, is_any_prefix in [("..%", False), ("%", True)]:
            sql = _make_lemgram_query_part(wf + suffpatt, corpora, limit)
            # print(sql)
            sql = korpplugins.KorpFunctionPlugin.call_chain(
                "filter_sql", sql, request._get_current_object())
            cursor.execute(sql)
            _retrieve_lemgrams(cursor, wf, modcase, is_any_prefix, result,
                               result_set)
            # print(repr(result))
            if len(result) >= limit:
                return result
    return result


def _retrieve_lemgrams(cursor, wf, modcase, is_any_prefix, result, result_set):
    # Note: Checking and filtering the results returned from the database
    # is probably not needed when using collation utf8(mb4)_bin, since it
    # is case-sensitive and does not collate "har", "hår" and "här". Using
    # a case-insensitive collation such as utf8(mb4)_swedish_ci or
    # utf8(mb4)_unicode_ci would not use the index, since the collation for
    # the table is utf8(mb4)_bin, so it would be unacceptably slow.
    # Case-insensitive matching would probably require a separate column
    # with preprocessed (lowercased, perhaps accents removed) lemgrams,
    # since apparently MySQL/MariaDB does not support specifying indexes
    # with different collations.
    #
    # The SQL LIKE pattern lemma..% also matches lemmas in which the lemma
    # searched for is followed by any number of full stops before the two
    # full stops that separate the POS tag in the lemgram. We wish to
    # filter out these incorrect lemmas.
    incorrect_lemma = wf + "..."
    for row in cursor:
        lemgram = row["lemgram"]
        if lemgram in result_set:
            continue
        mod_row = modcase(lemgram)
        if (mod_row.startswith(wf)
            and (is_any_prefix or not mod_row.startswith(incorrect_lemma))):
            result.append(lemgram)
            result_set.add(lemgram)


def _make_lemgram_query_part(pattern, corpora, limit):
    return ("(SELECT DISTINCT lemgram FROM lemgram_index"
            " WHERE lemgram LIKE '" + pattern + "'"
            + (" AND CORPUS IN (" + ','.join(["'" + corp + "'"
                                             for corp in corpora]) + ")"
               if corpora else '')
            # This would be too slow:
            # + " COLLATE 'utf8_swedish_ci'"
            # Order the result first by descending total frequency and
            # then by lemgram and then take the requested number of
            # rows at the beginning.
            + " GROUP BY lemgram"
            + " ORDER BY SUM(freq) DESC, lemgram"
            + " LIMIT " + str(limit)
            + ")")


def _encode_lemgram_result(lemgrams):
    return [{"class": ["entry"],
             "div": {"class": "source",
                     "resource": "lemgram_index"},
             "LexicalEntry": {"lem": lemgram}}
            for lemgram in lemgrams]
