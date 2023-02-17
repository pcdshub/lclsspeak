import os
import pathlib

MODULE_PATH = pathlib.Path(__file__).parent.resolve()
TESTS_PATH = MODULE_PATH / "tests"
DATA_PATH = MODULE_PATH / "data"


CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
