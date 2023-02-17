import dataclasses
import enum
from typing import Optional


@dataclasses.dataclass
class Definition:
    name: str
    definition: str
    source: str
    alternates: Optional[list[str]] = None
    tags: list[str] = dataclasses.field(default_factory=list)
    metadata: dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return bool(self.name and self.definition and self.source)


class StandardTag(str, enum.Enum):
    slacspeak = "slacspeak"

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return self.value
