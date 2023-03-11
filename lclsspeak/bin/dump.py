"""
`lclsspeak dump` will dump the acronym database.
"""

import argparse

from ..definition import Definition

from ..packaged import load_packaged_data

DESCRIPTION = __doc__


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    return argparser


def main():
    def by_name(defn: Definition):
        return (defn.name.lower(), defn.source)

    for item in sorted(load_packaged_data(), key=by_name):
        print(item)
