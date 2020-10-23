#!/usr/bin/python
# -*- coding: utf-8 -*-


# TODO: It might make sense to integrate this functionality into
# korp.cgi, either to count_lemgrams or as a separate command, to
# avoid duplicate work when first finding the lemgrams and then
# counting them in the frontend (services.coffee: korpApp.factory
# "lexicons"). Språkbanken use their Karp service.


import time
import cgi
import json
import MySQLdb
import korp_config as config


# The name of the MySQL database and table prefix
DBTABLE = "lemgram_index"


def main():
    starttime = time.time()
    print_header()

    # Convert form fields to regular dictionary
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field)) for field in form_raw.keys())

    wf = form.get("wf")
    corpora = form.get("corpus")
    limit = int(form.get("limit", 10))
    if corpora:
        corpora = corpora.split(',')
    result = {}
    try:
        result["div"] = get_lemgrams(wf, corpora, limit)
        result["count"] = len(result["div"])
        result["time"] = time.time() - starttime
        result["s"] = repr(result)
        print_object(result, form)
    except:
        import traceback, sys
        exc = sys.exc_info()
        error = {"ERROR": {"type": exc[0].__name__,
                           "value": str(exc[1]),
                           "traceback": traceback.format_exc().splitlines(),
                           },
                 "time": time.time() - starttime}
        print_object(error, form)


def get_lemgrams(wf, corpora, limit):
    conn = MySQLdb.connect(use_unicode=True,
                           charset="utf8",
                           **config.DBCONNECT)
    # Get Unicode objects even with collation utf8_bin; see
    # <http://stackoverflow.com/questions/9522413/mysql-python-collation-issue-how-to-force-unicode-datatype>
    conn.converter[MySQLdb.constants.FIELD_TYPE.VAR_STRING] = [
        (None, conn.string_decoder)]
    cursor = conn.cursor()
    result = query_lemgrams(cursor, wf, corpora, limit)[:limit]
    cursor.close()
    conn.close()
    return encode_lemgram_result(result)


def query_lemgrams(cursor, wf, param_corpora, limit):
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
            sql = make_lemgram_query_part(wf + suffpatt, corpora, limit)
            # print sql
            cursor.execute(sql)
            retrieve_lemgrams(cursor, wf, modcase, is_any_prefix,
                              result, result_set)
            # print repr(result)
            if len(result) >= limit:
                return result
    return result


def retrieve_lemgrams(cursor, wf, modcase, is_any_prefix, result, result_set):
    # Note: Checking and filtering the results returned from the
    # database is probably not needed when using collation utf8_bin,
    # since it is case-sensitive and does not collate "har", "hår" and
    # "här". Using a case-insensitive collation such as
    # utf8_swedish_ci or utf8_unicode_ci would not use the index,
    # since the collation for the table is utf8_bin, so it would be
    # unacceptably slow. Case-insensitive matching would probably
    # require a separate column with preprocessed (lowercased, perhaps
    # accents removed) lemgrams, since apparently MySQL/MariaDB does
    # not support specifying indexes with different collations.

    # The SQL LIKE pattern lemma..% also matches lemmas in which the
    # lemma searched for is followed by any number of full stops
    # before the two full stops that separate the POS tag in the
    # lemgram. We with to filter out these incorrect lemmas.
    incorrect_lemma = wf + "..."
    for row in cursor:
        if row[0] in result_set:
            continue
        mod_row = modcase(row[0].encode("utf-8"))
        if (mod_row.startswith(wf)
            and (is_any_prefix or not mod_row.startswith(incorrect_lemma))):
            result.append(row[0])
            result_set.add(row[0])


def make_lemgram_query_part(pattern, corpora, limit):
    return ("(select distinct lemgram from lemgram_index where lemgram like '"
            + pattern + "'"
            + (" and corpus in (" + ','.join(["'" + corp + "'"
                                             for corp in corpora]) + ")"
               if corpora else '')
            # This would be too slow:
            # + " collate 'utf8_swedish_ci'"
            # Order the result first by descending total frequency and
            # then by lemgram and then take the requested number of
            # rows at the beginning.
            + " group by lemgram"
            + " order by sum(freq) desc, lemgram"
            + " limit " + str(limit)
            + ")")


def encode_lemgram_result(lemgrams):
    return [{"class": ["entry"],
             "div": {"class": "source",
                     "resource": "lemgram_index"},
             "LexicalEntry": {"lem": lemgram}}
            for lemgram in lemgrams]


def print_header():
    """Prints the JSON header."""
    print "Content-Type: application/json"
    print "Access-Control-Allow-Origin: *"
    print


def print_object(obj, form):
    """Prints an object in JSON format.
    The CGI form can contain optional parameters 'callback' and 'indent'
    which change the output format.
    """
    callback = form.get("callback")
    if callback: print callback + "(",
    try:
        indent = int(form.get("indent"))
        print json.dumps(obj, sort_keys=True, indent=indent),
    except:
        print json.dumps(obj, separators=(",",":"))
    if callback: print ")",
    print


if __name__ == "__main__":
    main()
