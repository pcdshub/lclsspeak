"""
`lclsspeak dump` will dump the acronym database.
"""

import argparse
import dataclasses
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
        return json.dumps(dataclasses.asdict(defn), sort_keys=True)
    elif format == "html":
        def _td(text: str, escape: bool = True) -> str:
            if escape:
                text = html.escape(text)
            return f"<td>{text}</td>"

        def _tr(*items: str) -> str:
            text = "".join(items)
            return f"<tr>{text}</tr>"

        def _href(text: str, url: str, target: str = "_blank") -> str:
            return f'<a href="{url}" target={target}>{text}</a>'

        url = _href(defn.url.text, defn.url.url) if defn.url is not None else ""
        return _tr(
            _td(defn.name),
            _td(defn.definition),
            _td(defn.source),
            _td(url, escape=False),
        )

    raise ValueError(f"Unsupported format: {format}")


def format_header(format: str) -> str:
    if format == "html":
        return "<table><tr><th>Name</th><th>Definition</th><th>Source</th><th>Link</th></tr><tbody>"

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
