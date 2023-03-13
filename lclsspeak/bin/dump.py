"""
`lclsspeak dump` will dump the acronym database.
"""

import argparse
import html
import json

from ..definition import Definition

from ..packaged import load_packaged_data

DESCRIPTION = __doc__


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    argparser.add_argument(
        '--format',
        type=str,
        default="json",
    )

    return argparser


def dump(defn: Definition, format: str) -> str:
    if format == "json":
        return json.dumps(vars(defn), sort_keys=True)
    elif format == "html":
        def _td(text: str) -> str:
            text = html.escape(text)
            return f"<td>{text}</td>"

        def _tr(*items: str) -> str:
            text = "".join(items)
            return f"<tr>{text}</tr>"

        return _tr(
            *(
                _td(getattr(defn, attr))
                for attr in ("name", "definition", "source")
            )
        )
        
    raise ValueError(f"Unsupported format: {format}")


def format_header(format: str) -> str:
    if format == "html":
        return "<table><tr><th>Name</th><th>Definition</th><th>Source</th></tr><tbody>"

    return ""


def format_footer(format: str) -> str:
    if format == "html":
        return "</tbody></table>"

    return ""


def main(format: str = "json"):
    def by_name(defn: Definition):
        return (defn.name.lower(), defn.source)

    print(format_header(format))
    for item in sorted(load_packaged_data(), key=by_name):
        print(dump(item, format))
    print(format_footer(format))
