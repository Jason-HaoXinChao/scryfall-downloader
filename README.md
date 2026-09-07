# Scryfall Card Art Downloader

Download images for exact Magic: The Gathering printings from a deck list. Both a command-line interface and a small desktop GUI are included.

```text
1 Book of Mazarbul (LTR) 116
4 Lightning Bolt (CLB) 187
```

An optional set code and collector number select the printing. The quantity controls how many image files are created. Repeated lines for the same printing are combined.

## Features

- Exact printing lookup by set/collector number, or exact card name constrained to a set
- Complete card PNGs or artwork-only crops
- Double-faced card support
- Numbered output copies based on deck quantity
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

Bleed output has an exact 63×88 mm trim area plus 1.5 mm beyond every edge. At 300 DPI, the trim is 744×1039 pixels and the final 66×91 mm canvas is 780×1075 pixels. The source aspect ratio is preserved with a minimal center crop instead of being stretched. Mostly dark card perimeters use their dominant edge color. Other cards use an opaque inset underlay plus outward extension of the outermost pixels on all four sides. This avoids reflecting rounded transparent corners, text, or frame details into the bleed. Use `--bleed-mm` to change the bleed width and `--overwrite` to regenerate existing output.

Quantities greater than one produce numbered files such as `_copy-1.png`, `_copy-2.png`, and corresponding `_copy-1_bleed.png` outputs. Scryfall is contacted only once per printing; extra copies are made locally.

Double-sided cards download both face images as `_front.png` and `_back.png`. Quantities apply to both faces, so two copies create `_front_copy-1.png`, `_front_copy-2.png`, `_back_copy-1.png`, and `_back_copy-2.png`. If bleed processing is enabled, every face receives its own `_bleed.png` output.

Use `--image-type art_crop` to download only the illustration. Run `scryfall-download --help` for all options.

You can also run without installing the package:

```powershell
$env:PYTHONPATH = "src"
python -m scryfall_art_downloader deck.txt --output downloads
python -m scryfall_art_downloader.gui
```

## Deck-list format

Each card line must contain a quantity and card name. A set code and collector number may follow:

```text
1 Card Name (SET) 123
2x Another Card (ABC) A-45
SB: 1 Sideboard Card (XYZ) 7
1 Ephemerate (MH1)
1 Ephemerate
```

The set and collector number are optional. With a set but no collector number, the app asks Scryfall for the exact card name within that set. With neither, it uses an unconstrained exact-name lookup. A collector number remains the most precise way to select a particular variant and requires a set code.

Alternate titles printed on reskinned cards are matched against Scryfall's `flavor_name` and `printed_name` fields. If an exact-name lookup initially resolves to the rules card's default art, the app checks that card's printings and selects the printing whose alternate title matches the deck entry. A supplied set code also constrains this fallback.

Blank lines, comment lines beginning with `#` or `//`, and common section headings are ignored. A malformed line is reported with its line number.

A trailing `*E*` prismatic/etched marker is ignored, whether it appears after the card name or after the collector number. It does not affect proxy image selection.

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
