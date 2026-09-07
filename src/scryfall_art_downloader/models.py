from dataclasses import asdict, dataclass, field


@dataclass(frozen=True, slots=True)
class DeckEntry:
    quantity: int
    name: str
    set_code: str | None
    collector_number: str | None
    line_number: int
    source_line: str

    @property
    def printing_key(self) -> tuple[str, str]:
        scope = f"set:{self.set_code.casefold()}" if self.set_code else "set:any"
        if self.collector_number:
            identifier = f"number:{self.collector_number.casefold()}"
        else:
            identifier = f"name:{' '.join(self.name.casefold().split())}"
        return scope, identifier


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
