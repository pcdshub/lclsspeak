import io
import logging
import bs4
import pandas as pd
import dataclasses
import pathlib
import re
import subprocess

import requests
from . import util
from .definition import Definition
from typing import Any, Generator, Optional


logger = logging.getLogger(__name__)


def get_html_text_from_tag(soup: bs4.BeautifulSoup) -> str:
    # bs4 will remove tags for us, but some things like the nbsp equivalent
    # remain
    text = " ".join(soup.stripped_strings)
    text = text.replace("\xa0", " ")  # nbsp
    text = text.replace("\n", " ")
    # TODO
    return text.strip()


def table_to_dictionaries(table: bs4.element.Tag) -> Generator[dict[str, str], None, None]:
    current_headers = []
    for row in table.find_all("tr"):
        headers = row.find_all("th")
        data = row.find_all("td")
        if headers and data:
            # I don't know
            ...
        elif headers:
            current_headers = [get_html_text_from_tag(tag) for tag in headers]
        elif data and len(current_headers) == len(data):
            data = [get_html_text_from_tag(tag) for tag in data]
            yield dict(zip(current_headers, data))


def _append_data(existing: str | list[str], value: str, delimiter: str = "\n") -> str | list[str]:
    value = value.strip()
    if isinstance(existing, list):
        existing.append(value)
        return existing
    
    if not existing:
        return value
    return delimiter.join((existing.rstrip(), value))


@dataclasses.dataclass
class NamedData:
    column_to_key: dict[str, str]

    def map_dict_to_definition(self, row: dict[str, Any]) -> Definition:
        data = {
            "name": "",
            "definition": "",
            "source": "",
            "tags": [],
            "metadata": {"source_columns": []},
        }
        for col, key in self.column_to_key.items():
            value = row.get(col, None)
            if value is not None:
                value = str(value)
                if key == "metadata":
                    data["metadata"][col] = value
                else:
                    data[key] = _append_data(data.get(key, ""), value)
                    data["metadata"]["source_columns"].append(col)
       
        return Definition(**data)

    def map_series_to_definition(self, row: pd.Series) -> Definition:
        return self.map_dict_to_definition(dict(row))

    def map_to_definitions(self, df: pd.DataFrame) -> list[Definition]:
        return [self.map_series_to_definition(row) for _, row in df.iterrows()]


class DataSource:
    @property
    def data(self):
        return self.load()

    def load(self, use_cache: bool = True) -> list[Definition]:
        if self._data is None:
            self._data = list(self._load(use_cache=use_cache))
        return self._data

    def _load(self, use_cache: bool = True) -> list[Definition]:
        raise NotImplementedError


@dataclasses.dataclass
class CsvData(DataSource):
    url: str
    cached: pathlib.Path
    mapping: NamedData
    tags: list[str]
    encoding: str = "utf-8"
    _data: Optional[list[Definition]] = None

    @property
    def source(self) -> str:
        return self.url

    def _load(self, use_cache: bool = True) -> list[Definition]:
        if use_cache:
            with open(self.cached, "rt", encoding=self.encoding) as fp:
                source = fp.read()
        else:
            source = requests.get(self.url).text

        df = pd.read_csv(io.StringIO(source))
        for defn in self.mapping.map_to_definitions(df):
            defn.source = self.source
            yield defn


@dataclasses.dataclass
class HtmlTable:
    mapping: NamedData
    id: Optional[str] = None
    class_: Optional[str] = None

    def extract(self, source: bs4.BeautifulSoup | str) -> Generator[Definition, None, None]:
        if isinstance(source, bs4.BeautifulSoup):
            soup = source
        else:
            soup = bs4.BeautifulSoup(source, "html.parser")
        attrs = {}
        source = "html_table"
        if self.id:
            attrs["id"] = self.id
            source = f"html_table_{self.id}"
        if self.class_:
            attrs["class"] = self.class_
            source = f"html_table_{self.class_}"

        for table in soup.find_all("table", attrs):
            for dct in table_to_dictionaries(table):
                defn = self.mapping.map_dict_to_definition(dct)
                if not defn.source:
                    defn.source = source
                if defn.valid:
                    yield defn


class SourceScraper:
    def scrape(self, source: bs4.BeautifulSoup | str) -> Generator[Definition, None, None]:
        raise NotImplementedError


@dataclasses.dataclass
class RegexHtmlScraper(SourceScraper):
    tags: list[str]
    regexes: list[re.Pattern]

    def scrape(self, source: bs4.BeautifulSoup | str) -> Generator[Definition, None, None]:
        if isinstance(source, bs4.BeautifulSoup):
            soup = source
        else:
            soup = bs4.BeautifulSoup(source, "html.parser")
        valid_keys = set(Definition.__annotations__)
        for tag in self.tags:
            for element in soup.find_all(tag):
                text = get_html_text_from_tag(element)
                for regex in self.regexes:
                    for match in regex.finditer(text):
                        info = match.groupdict()
                        metadata = {}
                        for key, value in list(info.items()):
                            value = value.strip()
                            if key not in valid_keys:
                                info.pop(key)
                                metadata[key] = value
                            else:
                                info[key] = value
                        
                        if "source" not in info:
                            info["source"] = f"regex_scraper_{regex}"

                        defn = Definition(**info)
                        if defn.valid:
                            yield defn


def split_html_by_section(
    soup: bs4.BeautifulSoup, tag: str
) -> Generator[tuple[str, bs4.BeautifulSoup], None, None]:
    headers = soup.find_all(tag)
    if not headers:
        return
  
    for header in headers:
        buffer = []
        header_text = get_html_text_from_tag(header)
        for sibling in header.next_siblings:
            if sibling.name and sibling.name.lower() == tag:
                break
            buffer.append(str(sibling))
        yield header_text, bs4.BeautifulSoup("".join(buffer))


@dataclasses.dataclass
class SectionScraper(SourceScraper):
    section_names: list[str]
    tables: list[HtmlTable]
    section_tags: list[str] = dataclasses.field(
        default_factory=lambda: list(["h1"])
    )

    def scrape(self, source: bs4.BeautifulSoup | str) -> Generator[Definition, None, None]:
        if isinstance(source, bs4.BeautifulSoup):
            soup = source
        else:
            soup = bs4.BeautifulSoup(source, "html.parser")
        for section_tag in self.section_tags:
            for title, section_soup in split_html_by_section(soup, section_tag):
                if title not in self.section_names and title.lower() not in self.section_names:
                    continue

                for table in self.tables or []:
                    yield from table.extract(section_soup)


@dataclasses.dataclass
class WebsiteData(DataSource):
    url: str
    cached: pathlib.Path
    token: Optional[str] = None
    tables: Optional[list[HtmlTable]] = None
    scrapers: Optional[list[SourceScraper]] = None
    _data: Optional[list[Definition]] = None
    encoding: str = "utf-8"

    @property
    def source(self) -> str:
        return self.url or self.cached.name

    def _load(self, use_cache: bool = True) -> Generator[Definition, None, None]:
        if use_cache:
            with open(self.cached, "rt", encoding=self.encoding) as fp:
                source = fp.read()
        else:
            # TODO: token Authorization: Bearer (token)
            source = requests.get(self.url).text

        for table in self.tables or []:
            for defn in table.extract(source):
                defn.source = self.source
                yield defn

        for scraper in self.scrapers or []:
            for defn in scraper.scrape(source):
                defn.source = self.source
                yield defn


@dataclasses.dataclass
class PandocData(WebsiteData):
    input_format: str = "docx"
    _html_data: Optional[str] = None

    @property
    def source(self) -> str:
        return self.url or self.cached.name

    def _convert_to_html(self) -> str:
        raw_html_bytes = subprocess.check_output(
            [
                "pandoc",
                "-f",
                self.input_format,
                "-t",
                "html",
                str(self.cached.resolve()),
            ]
        )
        return raw_html_bytes.decode("utf-8")

    def _load(self, use_cache: bool = True) -> Generator[Definition, None, None]:
        if self._html_data is None or not use_cache:
            self._html_data = self._convert_to_html()
        source = self._html_data

        for table in self.tables or []:
            for defn in table.extract(source):
                defn.source = self.source
                yield defn

        for scraper in self.scrapers or []:
            for defn in scraper.scrape(source):
                defn.source = self.source
                yield defn


_packaged_data: list[DataSource] = [
    CsvData(
        url="https://docs.google.com/spreadsheets/d/1SeQhfwZ6O-wg8tyr_MCQZY1boJC-6j3N6EzexfZB-AU",
        cached=util.DATA_PATH / "pcds_ccc.csv",
        mapping=NamedData(
            column_to_key={
                "ccc": "name",
                "Description": "definition",
                "Subject (Controls)": "tags",
                "Sub Category": "tags",
            },
        ),
        tags=[],
    ),
]

_external_data: list[DataSource] = [
    # LCLS naming conventions tables:
    # ['Area', 'Physical Location']
    # ['Area', 'Position Prefix Codes', 'Physical Position']
    # ['Attribute', 'Function Affected or Parameter Described', 'Controllable']
    # ['DeviceType Name', 'Purpose']
    # ['Subsystem Prefix for Standard IOC', 'Alarm IOC', 'Subsystem Prefix for Network Display and Alarm Config Filenames', 'Subsystem Description']
    # ['Value', 'Device Type', 'Controllable']

    WebsiteData(
        url="https://confluence.slac.stanford.edu/display/LCLSControls/LCLS+Naming+Conventions",
        cached=util.DATA_PATH / "LCLS+Naming+Conventions.html",
        token=util.CONFLUENCE_TOKEN,
        tables=[
            HtmlTable(
                mapping=NamedData(
                    column_to_key={
                        # Names
                        "Area": "name",
                        "Attribute": "name",
                        "DeviceType Name": "name",
                        "IOC type": "name",
                        "Subsystem Prefix for Standard IOC": "name",
                        "Value": "name",
                        # Definitions
                        "Controllable": "metadata",
                        "Description": "definition",
                        "Device Type": "definition",
                        "Function Affected or Parameter Described": "definition",
                        "Physical Location": "definition",
                        "Purpose": "definition",
                    },
                ),
            ),
            HtmlTable(
                mapping=NamedData(
                    column_to_key={
                        "Subsystem Prefix for Network Display and Alarm Config Filenames": "name",
                        "Subsystem Description": "definition",
                    },
                ),
            ),
        ],
    ),
    WebsiteData(
        url="https://confluence.slac.stanford.edu/display/L2SI/MODS+Nomenclature",
        cached=util.DATA_PATH / "MODS+Nomenclature.html",
        token=util.CONFLUENCE_TOKEN,
        tables=[
            HtmlTable(
                mapping=NamedData(
                    column_to_key={
                        # Names
                        "Acronym": "name",
                        # Definitions
                        "Common Name": "definition",
                        "Description": "definition",
                        # Metadata
                        "Hutch": "metadata",
                        "Platform": "metadata",
                        "Optical Origins": "metadata",
                    },
                ),
            ),
        ],
    ),
    WebsiteData(
        url="https://confluence.slac.stanford.edu/display/TBD/Acronyms+that+are+commonly+encountered",
        cached=util.DATA_PATH / "Acronyms+that+are+commonly+encountered.html",
        token=util.CONFLUENCE_TOKEN,
        scrapers=[
            RegexHtmlScraper(
                tags=["li"],
                regexes=[
                    re.compile(r"(?P<name>[^=]+)\s*=\s*(?P<definition>.+)"),
                ]
            )
        ],
    ),
]


default_docx_tables = [

]
default_docx_scrapers = [
    SectionScraper(
        section_names=["acronyms"],
        tables=[
            HtmlTable(
                mapping=NamedData(
                    column_to_key={
                        "ECS": "name",
                        "Experiment Control Systems Department": "definition",
                    }
                )
            )
        ]
    )
]


def _add_packaged_docx_files():
    for fn in util.DATA_PATH.glob("*"):
        if fn.suffix.lower() in (".docx", ):
            source = PandocData(
                url="",  # sorry
                cached=util.DATA_PATH / fn,
                tables=default_docx_tables,
                scrapers=default_docx_scrapers,
            )
            _packaged_data.append(source)


def load_packaged_data() -> list[Definition]:
    return [
        item
        for pkg in _packaged_data + _external_data
        for item in pkg.load(use_cache=True)
    ]

_add_packaged_docx_files()
