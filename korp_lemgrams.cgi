#!/usr/bin/python
# -*- coding: utf-8 -*-


import time
import cgi
import json
import MySQLdb


# The name of the MySQL database and table prefix
DBNAME = "korp"
DBTABLE = "lemgram_index"
# Username and password for database access
DBUSER = "korp"
DBPASSWORD = ""


def main():
    """The main CGI handler; reads the 'command' parameter and calls
    the same-named function with the CGI form as argument.

    Global CGI parameter are
     - command: (default: 'info' or 'query' depending on the 'cqp' parameter)
     - callback: an identifier that the result should be wrapped in
     - encoding: the encoding for interacting with the corpus (default: UTF-8)
     - indent: pretty-print the result with a specific indentation (for debugging)
     - debug: if set, return some extra information (for debugging)
    """
    starttime = time.time()
    print_header()
    
    # Convert form fields to regular dictionary
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field)) for field in form_raw.keys())
    
    wf = form.get("wf")
    result = {}
    try:
        result["div"] = get_lemgrams(wf)
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


def get_lemgrams(wf):
    conn = MySQLdb.connect(host = "localhost",
                           user = DBUSER,
                           passwd = DBPASSWORD,
                           db = DBNAME,
                           use_unicode = True,
                           charset = "utf8")
    cursor = conn.cursor()
    sql = ("SELECT lemgram from lemgram_index where lemgram like '" + wf
           + "%' limit 10;")
    result = []
    cursor.execute(sql)
    for row in cursor:
        # We need this check here, since a search for "hår" also returns "här" and "har".
        if row[0].encode("utf-8").startswith(wf):
            result.append({"class": ["entry"],
                           "div": {"class": "source",
                                   "resource": "lemgram_index"},
                           "LexicalEntry": {"lem": row[0]}})
    cursor.close()
    conn.close()
    return result


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
