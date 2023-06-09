import dataclasses
from typing import Optional

import bs4
import requests

from . import util
from .definition import URL, Definition, StandardTag

SLACSPEAK_URL = "https://www.slac.stanford.edu/history/slacspeak/"

# TODO: there are some manual required fixes in slacspeak to correctly parse
# the html (unclosed <dd> tags)


@dataclasses.dataclass
class _ParserState:
    dd: Optional[str] = None
    dt: Optional[str] = None


def parse_slacspeak(source: str) -> list[Definition]:
    definitions = []

    soup = bs4.BeautifulSoup(source, "html.parser")
    content, = soup.find_all("div", id="maincontent")
    entries = content.find_all(name=("dd", "dt"))

    state = _ParserState()
    for entry in entries:
        setattr(state, entry.name.lower(), entry.text)
        if state.dd and state.dt:
            definitions.append(
                Definition(
                    name=state.dt,
                    definition=state.dd,
                    source="slacspeak",
                    tags=[StandardTag.slacspeak],
                    url=URL(
                        url="https://www.slac.stanford.edu/history/slacspeak/",
                        text="slacspeak",
                    )
                ),
            )
            state.dd = None
            state.dt = None
    return definitions


def get_slacspeak() -> list[Definition]:
    return parse_slacspeak(requests.get(SLACSPEAK_URL).text)


def get_packaged_slacspeak() -> list[Definition]:
    with open(util.TESTS_PATH / "slacspeak.html", encoding="ISO-8859-1") as fp:
        speak = fp.read()
    return parse_slacspeak(speak)
