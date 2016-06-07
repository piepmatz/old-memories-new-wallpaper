from __future__ import print_function
import sys


def error(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def to_unicode(string):
    """
    Expects a string and returns a unicode.
    For Python 2, the string is converted to a unicode with utf-8 encoding to handle German Umlaute.
    For Python 3, the string is returned unchanged as it is a unicode already.

    Why is this method needed at all? The alternatives do not work for Umlaute for both Python 2 and 3.
    six.u() is only safe in Python 2 for ascii characters. str from builtins needs an explicit encoding that fails
    with Python 3.
    """
    try:
        return unicode(string, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return unicode(string, encoding="cp1252")  # similar to latin1, used by Windows
        except UnicodeDecodeError:
            error("Your files have some difficult names. Switching to Python 3 should solve this problem.")
    except NameError:
        return string
