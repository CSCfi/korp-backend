#! /usr/bin/python
# -*- mode: Python; -*-

# jpiitula@ling.helsinki.fi for making Korp authentication work in
# FIN-CLARIN; HTTP Basic Authentication for development version, and
# Martin's Shibboleth session for production use (trusting
# REMOTE_USER, which korp.cgi passes as remote_user).

# This server script is meant to receive HTTP Basic Authentication
# credentials (username and password in plain) from Korp backend
# (korp.cgi) and then return the list of authorized korpora in JSON (I
# think).

# This script may be written to log some info in a file -- set
# level=logging.INFO for that, or perhaps that code should now be
# removed.

from __future__ import print_function

import cgi
import json
import MySQLdb

import sys
sys.stderr = sys.stdout

AUTH_DBNAME = "korp_auth"
AUTH_DBUSER = "korp"
AUTH_DBPASSWORD = ""

def main():
    print_header()

    form_raw = cgi.FieldStorage(keep_blank_values=True)
    form = dict((field, form_raw.getvalue(field))
                for field in form_raw.keys())
    logging.info('%s', form)

    conn = MySQLdb.connect(host = "localhost",
                           user = AUTH_DBUSER,
                           passwd = AUTH_DBPASSWORD,
                           db = AUTH_DBNAME,
                           use_unicode = True,
                           charset = "utf8")
    cursor = conn.cursor()

    authenticated, academic = False, False
    if 'remote_user' in form:
        username = form['remote_user']
        authenticated = True
        # Open: How does one get the ACA bit (researcher status in
        # home organization) in Shibboleth?
    else:
        username = form.get('username', None)
        password = form.get('password', '')
        # Faking the ACA bit - not for production use:
        if username.endswith('+ACA'):
            username, _ = username.rsplit('+')
            academic = True
        cursor.execute('''
        select secret from auth_secret
        where person = %s''', [username])
        secret = cursor.fetchone()
        if secret is not None and secret[0] == password:
            authenticated = True

    # We can grant ACA status to people locally:
    if  authenticated and not academic:
        cursor.execute('''
        select 1 from auth_academic
        where person = %s''', [username])
        if cursor.fetchone():
            academic = True

    if authenticated:
        cursor.execute('''
        select corpus from auth_license
        where license = 'ACA' and %s = True
        union distinct
        select corpus from auth_allow
        where person = %s''', [academic, username])
        corpora = [ corpus for corpus, in cursor ]

        result = dict(authenticated=True,
                      permitted_resources=dict(username=username,
                                               corpora=corpora))
    else:
        result = dict(authenticated=False)

    result = json.dumps(result)
    logging.info('result: %s', result)
    print(result)

def print_header():
    '''Copied from korp.cgi - may not be quite right here'''
    print("Content-Type: application/json")
    print("Access-Control-Allow-Origin: *")
    print("Access-Control-Allow-Methods: GET, POST")
    print("Access-Control-Allow-Headers: Authorization")
    print()

if __name__ == '__main__':
    import logging
    import os
    logging.basicConfig(filename='/dev/null',
                        format=('[auth ' + str(os.getpid()) +
                                ' @ %(asctime)s] %(message)s'),
                        level=logging.WARNING) # in logging version, INFO

    logging.info('entering auth.cgi')
    main()
    logging.info('exiting auth.cgi')
