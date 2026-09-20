# csv-column-data-migrator

Fills one CSV column from whichever of several source columns is set, row by row.

## What it does

The tool reads a CSV, looks at a list of source columns in the order you give them, and sets one target column per row:

| Sources set in the row | Result |
| --- | --- |
| exactly one | the target takes that value |
| more than one | depends on `--on-conflict`: `keep` leaves the target as it is, `first` takes the earliest set source in the list, `last` takes the latest |
| none | the target stays as it is |

A field that is empty or only whitespace counts as unset. Values are copied as text, so a date keeps whatever format the export used. Every other column passes through untouched, in the input's column order.

Before parsing, the tool replaces vertical tab characters (`\x0b`) with a space. `--no-clean` skips that step.

The defaults are the ones the tool was written for: target `createdAt`, sources `Subscribed` then `Joined`, `--on-conflict keep`, comma delimiter. Without options it behaves as the original one-off script did.

## Why this exists

I moved a newsletter audience from one service to another. The source export held each contact's date in one of two columns depending on how the contact had been added: `Subscribed` for people who signed up through a form, `Joined` for people who were imported or added another way. The importing service wanted one `createdAt`.

A few fields also contained vertical tab characters, and the CSV reader split those contacts across two rows.

So the script fills `createdAt` from whichever column is set, leaves rows where both or neither are set untouched so no date is guessed, and cleans the control characters first.

## Other uses

The same shape shows up whenever two columns hold the same fact for different rows:

- a CRM export with a `Created` and an `Imported On` column after a migration
- an order export where two shop backends wrote `Ordered At` and `Placed At`
- a user table with `signup_date` next to a `legacy_created` column
- any merged spreadsheet where an old and a new column for the same fact coexist

The tool coalesces one target from ordered sources per row. It does not parse dates, compare values, or merge rows.

## Requirements

- Python 3.12 or newer (tested with 3.12 and 3.13)
- pandas, pinned in `pyproject.toml`

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

This installs the `csv-coalesce-columns` command. `python3 main.py` takes the same arguments and works from a checkout once pandas is installed.

## Usage

```bash
csv-coalesce-columns <input.csv> <output.csv> [options]
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--target COLUMN` | `createdAt` | column to fill |
| `--source COLUMN` | `Subscribed`, then `Joined` | column to fill from; repeat the option, order sets precedence |
| `--on-conflict keep\|first\|last` | `keep` | what to do when more than one source is set |
| `--delimiter CHAR` | `,` | field delimiter, `'\t'` for tab |
| `--no-clean` | off | keep vertical tab characters |
| `--verbose` | off | log column names, a sample before and after, and one line per changed row on stderr |

The input needs a header row with the target and every source column. If one is missing, the tool exits with status 1 and names the missing columns. The output is written with the same delimiter.

The default output is one count per source (rows where only that source is set) and one count of rows where more than one source is set:

```
Rows with only Subscribed set: 2
Rows with only Joined set: 1
Rows with more than one source set: 1
```

A run with your own column names:

```bash
csv-coalesce-columns users.csv users-out.csv \
  --target created --source signup_date --source legacy_created --on-conflict last
```

## Examples

`examples/subscribers-before.csv` is an invented newsletter export with one row per case from the table above, plus a row whose name field contains a vertical tab. `examples/subscribers-after.csv` is what the default invocation produces from it.

```bash
csv-coalesce-columns examples/subscribers-before.csv output.csv
cmp output.csv examples/subscribers-after.csv
```

`examples/orders-before.csv` is an invented semicolon-separated order export with `Ordered At` and `Placed At` columns and an empty `created_at`. `examples/orders-after.csv` is the result of:

```bash
csv-coalesce-columns examples/orders-before.csv output.csv \
  --target created_at --source 'Ordered At' --source 'Placed At' --delimiter ';'
cmp output.csv examples/orders-after.csv
```

`cmp` prints nothing when the two files match.

## Tests

```bash
pip install -e '.[dev]'
python -m pytest
```

## Limitations

- Values are compared as text. No date parsing happens, so the copied value keeps whatever format the export used, and `first` and `last` follow the order of the `--source` options, not the dates.
- The cleanup step only knows about vertical tabs. Other control characters pass through.
- The whole file is read into memory.

## License

MIT, see `LICENSE`.
