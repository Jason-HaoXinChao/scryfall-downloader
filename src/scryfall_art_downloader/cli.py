import argparse
import json
import sys
from pathlib import Path

from .client import ScryfallClient
from .downloader import download_entries
from .parser import DeckParseError, parse_deck_list, unique_printings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download exact card printings from a Scryfall-formatted deck list."
    )
    parser.add_argument("deck", type=Path, help="UTF-8 deck-list text file")
    parser.add_argument("-o", "--output", type=Path, default=Path("downloads"))
    parser.add_argument("--image-type", choices=("png", "art_crop"), default="png")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--add-bleed",
        action="store_true",
        help="also create 750x1050 cards with a 36-pixel print bleed",
    )
    parser.add_argument(
        "--bleed-pixels",
        type=int,
        default=36,
        help="bleed width in pixels (default: 36)",
    )
    parser.add_argument("--delay", type=float, default=0.15, help="seconds between API requests")
    parser.add_argument("--report", type=Path, help="write a JSON result report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.add_bleed and args.image_type != "png":
        print("Error: --add-bleed requires --image-type png.", file=sys.stderr)
        return 2
    try:
        text = args.deck.read_text(encoding="utf-8-sig")
        entries = unique_printings(parse_deck_list(text))
        client = ScryfallClient(delay=args.delay)
    except (OSError, DeckParseError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Found {len(entries)} unique printing(s).")

    def show_progress(index, total, result):
        message = f" - {result.message}" if result.message else ""
        print(f"[{index}/{total}] {result.status.upper()}: {result.entry.name}{message}")

    results = download_entries(
        entries,
        args.output,
        image_type=args.image_type,
        overwrite=args.overwrite,
        add_bleed_edge=args.add_bleed,
        bleed_pixels=args.bleed_pixels,
        client=client,
        progress=show_progress,
    )
    if args.report:
        args.report.write_text(
            json.dumps([result.to_dict() for result in results], indent=2),
            encoding="utf-8",
        )

    failed = sum(result.status == "failed" for result in results)
    print(f"Finished with {failed} failure(s). Output: {args.output.resolve()}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
