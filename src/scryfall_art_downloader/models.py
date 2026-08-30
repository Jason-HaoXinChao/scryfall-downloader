from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class DeckEntry:
    quantity: int
    name: str
    set_code: str
    collector_number: str
    line_number: int
    source_line: str

    @property
    def printing_key(self) -> tuple[str, str]:
        return self.set_code.casefold(), self.collector_number.casefold()


@dataclass(slots=True)
class DownloadResult:
    entry: DeckEntry
    status: str
    files: list[str] = field(default_factory=list)
    processed_files: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["entry"] = asdict(self.entry)
        return result
