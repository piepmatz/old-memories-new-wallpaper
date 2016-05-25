from __future__ import print_function
import sys


def error(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)
