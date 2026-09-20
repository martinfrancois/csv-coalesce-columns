# csv-column-data-migrator

Fills the empty `createdAt` column of a subscriber CSV export from its `Subscribed` or `Joined` column.

## What it does

The script reads a CSV with the columns `Subscribed`, `Joined` and `createdAt` and rewrites `createdAt` row by row:

| `Subscribed` | `Joined` | Result |
| --- | --- | --- |
| set | empty | `createdAt` becomes the `Subscribed` value |
| empty | set | `createdAt` becomes the `Joined` value |
| set | set | `createdAt` stays as it is |
| empty | empty | `createdAt` stays as it is |

Before parsing, it replaces vertical-tab characters (`\x0b`) with a space so that a stray control character inside a quoted field cannot split one record over two lines. Every other column passes through untouched. The script logs a count per case and one debug line per changed row.

I wrote it for a one-off migration of a mailing list export. It is small enough to read in full before you run it on your own data.

## Requirements

- Python 3.12 or newer (tested with 3.12 and 3.13)
- pandas, pinned in `requirements.txt`

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python3 main.py <input.csv> <output.csv>
```

The input must have a header row with `Subscribed`, `Joined` and `createdAt` columns. If one is missing the script exits with status 1 and names the missing columns. The output keeps the column order of the input.

## Example

`examples/subscribers-before.csv` is an invented export with one row per case from the table above, plus a row whose name field contains a vertical tab. `examples/subscribers-after.csv` is what the script produces from it.

```bash
python3 main.py examples/subscribers-before.csv output.csv
cmp output.csv examples/subscribers-after.csv
```

`cmp` prints nothing when the two files match.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Limitations

- The cleanup step writes `<input.csv>.cleaned` next to the input file and does not delete it afterwards.
- Values are compared as text. A field that only contains whitespace counts as empty, but no date parsing happens, so the copied value keeps whatever format the export used.
- Logging is fixed at debug level, so large files produce a lot of output on stderr.

## License

MIT, see `LICENSE`.
