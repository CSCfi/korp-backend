#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
korp.cgi is a CGI interface for querying the corpora that are available on the server.

Currently it acts as a wrapper for the CQP querying language of Corpus Workbench.

http://spraakbanken.gu.se/korp/
"""

from subprocess import Popen, PIPE
from collections import defaultdict
from concurrent import futures

import sys
import os
import random
import time
import cgi
import re
import json
import MySQLdb
import zlib
import urllib, urllib2, base64, md5
from Queue import Queue, Empty
import threading
import ast
import logging

################################################################################
# These variables could be changed depending on the corpus server

# Put PROTECTED_FILE contents, with PUB, ACA and RES, and other
# authorization information in the database (jpiitula Dec 2013)
AUTH_DBNAME = "korp_auth"
AUTH_DBUSER = "korp"
AUTH_DBPASSWORD = ""

# URL to authentication server
AUTH_SERVER = "http://localhost/cgi-bin/korp/auth.cgi"
# Secret string used when communicating with authentication server
AUTH_SECRET = ""

PAGEFILE_DIR = "/v/corpora/pages"

# Path to log file; use /dev/null to disable logging
LOG_FILE = "/v/korp/log/korp-cgi.log"
# Log level: set to logging.DEBUG for also logging actual CQP
# commands, logging.WARNING for only warnings and errors,
# logging.CRITICAL to disable logging
LOG_LEVEL = logging.DEBUG

######################################################################
# These variables should probably not need to be changed

# Regular expressions for parsing CGI parameters
IS_NUMBER = re.compile(r"^\d+$")
IS_IDENT = re.compile(r"^[\w\-,|]+$")

################################################################################
# And now the functions corresponding to the CGI commands

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

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # Open unbuffered stdout
    
    # Convert form fields to regular dictionary
    form_raw = cgi.FieldStorage()
    form = dict((field, form_raw.getvalue(field)) for field in form_raw.keys())

    # Configure logging
    loglevel = logging.DEBUG if "debug" in form else LOG_LEVEL
    logging.basicConfig(filename=LOG_FILE,
                        format=('[%(filename)s %(process)d' +
                                ' %(levelname)s @ %(asctime)s]' +
                                ' %(message)s'),
                        level=loglevel)
    # Log remote IP address and CGI parameters
    logging.info('IP: %s', cgi.os.environ.get('REMOTE_ADDR'))
    logging.info('Params: %s', form)
    
    try:
        showpage(form)
        elapsed_time = time.time() - starttime
        # Log elapsed time
        logging.info("Elapsed: %s", str(elapsed_time))
    except:
        import traceback
        exc = sys.exc_info()
        error = {"ERROR": {"type": exc[0].__name__,
                           "value": str(exc[1])
                           },
                 "time": time.time() - starttime}
        trace = traceback.format_exc().splitlines()
        if "debug" in form:
            error["ERROR"]["traceback"] = trace
        print_header("application/json")
        print_object(error, form)
        # Traceback for logging
        error["ERROR"]["traceback"] = trace
        # Log error message with traceback and elapsed time
        logging.error("%s", error["ERROR"])
        logging.info("Elapsed: %s", str(error["time"]))


class KorpPageAccessError(Exception):
    pass


class KorpAuthenticationError(Exception):
    pass


def showpage(form):
    """ """

    assert_key('corpus', form, IS_IDENT, True)
    corpus = form.get('corpus')
    check_authentication([corpus.upper()])
    
    assert_key('page', form, r'^\S+$', True)
    page = form.get('page')
    try:
        with open(os.path.join(PAGEFILE_DIR, corpus, page), 'r') as f:
            print_header('text/'
                         + ('html' if page.endswith('.html') else 'plain'))
            for line in f:
                sys.stdout.write(line)
    except IOError, e:
        raise KorpPageAccessError(
            'Cannot access page \'' + page + '\' for corpus ' + corpus
            + ' (error code ' + str(e.errno) + ')')


def assert_key(key, form, regexp, required=False):
    """Check that the value of the attribute 'key' in the CGI form
    matches the specification 'regexp'. If 'required' is True, then
    the key has to be in the form.
    """
    value = form.get(key, "")
    if value and not isinstance(value, list):
        value = [value]
    if required and not value:
        raise KeyError("Key is required: %s" % key)
    if not all(re.match(regexp, x) for x in value):
        pattern = regexp.pattern if hasattr(regexp, "pattern") else regexp
        raise ValueError("Value(s) for key %s do(es) not match /%s/: %s" % (key, pattern, value))


def print_header(content_type):
    """Prints the JSON header."""
    print "Content-Type: " + content_type
    print "Access-Control-Allow-Origin: *"
    print "Access-Control-Allow-Methods: GET, POST"
    print "Access-Control-Allow-Headers: Authorization"
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
        out = json.dumps(obj, sort_keys=True, indent=indent)
        out = out[1:-1] if form.get("incremental", "").lower() == "true" else out
        print out,
    except:
        out = json.dumps(obj, separators=(",",":"))
        out = out[1:-1] if form.get("incremental", "").lower() == "true" else out
        print out,
    if callback: print ")",


def authenticate(_=None):
    """Authenticates a user against AUTH_SERVER.
    """
    remote_user = cgi.os.environ.get('REMOTE_USER')
    auth_header = cgi.os.environ.get('HTTP_AUTH_HEADER')
    logging.debug('auth env: %s', cgi.os.environ)

    if remote_user:
        # In which order should we check the affiliation variables?
        affiliation = (cgi.os.environ.get('HTTP_UNSCOPED_AFFILIATION') or
                       cgi.os.environ.get('HTTP_AFFILIATION') or '')
        postdata = {
            "remote_user": remote_user,
            "affiliation": affiliation.lower()
        }
    elif auth_header and auth_header.startswith("Basic "):
        user, pw = base64.b64decode(auth_header[6:]).split(":")

        postdata = {
            "username": user,
            "password": pw,
            "checksum": md5.new(user + pw + AUTH_SECRET).hexdigest()
        }
    else:
        return dict(username=None)

    try:
        contents = urllib2.urlopen(AUTH_SERVER, urllib.urlencode(postdata)).read()
        auth_response = json.loads(contents)
    except urllib2.HTTPError:
        raise KorpAuthenticationError("Could not contact authentication server.")
    except ValueError:
        raise KorpAuthenticationError("Invalid response from authentication server.")
    except:
        raise KorpAuthenticationError("Unexpected error during authentication.")

    # Response contains username and corpora, or username=None
    return auth_response.get('permitted_resources', {})


def check_authentication(corpora):
    """Raises an exception if any of the corpora are protected and the
    user is not authorized to access them (by AUTH_SERVER)."""
    
    conn = MySQLdb.connect(host = "localhost",
                           user = AUTH_DBUSER,
                           passwd = AUTH_DBPASSWORD,
                           db = AUTH_DBNAME,
                           use_unicode = True,
                           charset = "utf8")
    cursor = conn.cursor()
    cursor.execute('''
    select corpus from auth_license
    where license = 'ACA' or license = 'RES'
    ''')
    protected = [ corpus for corpus, in cursor ]
    cursor.close()
    conn.close()

    logging.debug('corpora: %s', corpora)
    logging.debug('protected: %s', protected)

    if protected:
        auth = authenticate()
        logging.debug('auth: %s', auth)
        authorized = auth.get('corpora', [])
        logging.debug('authorized: %s', authorized)
        unauthorized = [ corpus for corpus in corpora
                         if corpus in protected
                         and corpus not in authorized ]
        logging.debug('unauthorized: %s', unauthorized)

        if unauthorized:
            raise KorpAuthenticationError("You do not have access to the following corpora: %s" % ", ".join(unauthorized))


if __name__ == "__main__":
    main()
