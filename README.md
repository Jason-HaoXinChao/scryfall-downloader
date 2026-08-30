# Scryfall Card Art Downloader

Download images for exact Magic: The Gathering printings from a deck list. Both a command-line interface and a small desktop GUI are included.

```text
1 Book of Mazarbul (LTR) 116
4 Lightning Bolt (CLB) 187
```

The set code and collector number select the exact printing. Duplicate printings are downloaded once, regardless of deck quantity.

## Features

- Exact printing lookup through Scryfall's `/cards/:set/:collector_number` API
- Complete card PNGs or artwork-only crops
- Double-faced card support
- Arena-style deck sections and `SB:` lines
- Safe filenames, existing-file skipping, and partial-download cleanup
- Optional print-bleed processing adapted from `the-bleed-edgemaxxer`
- API request pacing that follows Scryfall's published guidance

## Run from source

Python 3.10 or newer is required.

```powershell
git clone https://github.com/Jason-HaoXinChao/scryfall-downloader.git
cd scryfall-downloader
python -m pip install -e .
```

Start the GUI:

```powershell
scryfall-download-gui
```

Or use the command line:

```powershell
scryfall-download deck.txt --output downloads --image-type png
```

Add `--add-bleed` to keep the downloaded PNG and create a second `_bleed.png` file:

```powershell
scryfall-download deck.txt --output downloads --image-type png --add-bleed
```

Bleed output is normalized to 750×1050, gains a 36-pixel edge on every side, and is saved as an 822×1122 PNG at 300 DPI. Mostly dark card perimeters use their dominant edge color. Other cards mirror the top and side edges, matching the original bleed-edgemaxxer behavior. Use `--bleed-pixels` to change the width.

Use `--image-type art_crop` to download only the illustration. Run `scryfall-download --help` for all options.

You can also run without installing the package:

```powershell
$env:PYTHONPATH = "src"
python -m scryfall_art_downloader deck.txt --output downloads
python -m scryfall_art_downloader.gui
```

## Deck-list format

Each card line must contain a quantity, card name, set code, and collector number:

```text
1 Card Name (SET) 123
2x Another Card (ABC) A-45
SB: 1 Sideboard Card (XYZ) 7
```

Blank lines, comment lines beginning with `#` or `//`, and common section headings are ignored. A malformed line is reported with its line number.

## Scryfall API use

The app sends identifying `User-Agent` and `Accept` headers and waits at least 100 milliseconds between API requests. Do not remove the request pacing. For very large collections, use [Scryfall bulk data](https://scryfall.com/docs/api/bulk-data) rather than repeated API lookups.

Card images and Magic: The Gathering content are property of their respective copyright holders. This project is intended as a personal download utility and is not affiliated with or endorsed by Scryfall or Wizards of the Coast. Follow the [Scryfall terms](https://scryfall.com/docs/api) and applicable image-use policies.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## License

The source code is available under the MIT License. This license does not grant rights to downloaded card images.
