#!/usr/bin/env python3
"""Fill one CSV column from ordered source columns, row by row."""

import argparse
import csv
import io
import logging
import sys

import pandas as pd

DEFAULT_TARGET = "createdAt"
DEFAULT_SOURCES = ("Subscribed", "Joined")
CONFLICT_CHOICES = ("keep", "first", "last")
DELIMITER_ESCAPES = {"\\t": "\t"}


def clean_control_chars(text: str) -> str:
    """Replace every vertical tab character with a space."""
    return text.replace("\x0b", " ")


def count_cases(df: pd.DataFrame, sources) -> dict:
    """Count the rows where exactly one source is set, per source, and the rows where several are."""
    set_masks = [df[name].str.strip().ne("") for name in sources]
    set_count = sum(set_masks)
    counts = {
        f"only {name} set": int((mask & set_count.eq(1)).sum())
        for name, mask in zip(sources, set_masks)
    }
    counts["more than one source set"] = int(set_count.gt(1).sum())
    return counts


def coalesce_column(
    df: pd.DataFrame,
    target: str = DEFAULT_TARGET,
    sources=DEFAULT_SOURCES,
    on_conflict: str = "keep",
) -> pd.DataFrame:
    """Set `target` from the one non-empty source per row.

    A value that is empty or only whitespace counts as unset. When several
    sources are set, `keep` leaves the target as it is, `first` takes the
    earliest set source in `sources` and `last` the latest. When no source is
    set the target stays as it is.
    """
    if on_conflict not in CONFLICT_CHOICES:
        raise ValueError(f"on_conflict must be one of {CONFLICT_CHOICES}, got {on_conflict!r}")

    def pick(row):
        present = [(name, row[name].strip()) for name in sources if row[name].strip()]
        if not present or (len(present) > 1 and on_conflict == "keep"):
            return row[target]
        name, value = present[-1] if on_conflict == "last" else present[0]
        logging.debug("Row %d: %s %r -> %r (%s)", row.name, target, row[target], value, name)
        return value

    if not df.empty:
        df[target] = df.apply(pick, axis=1)
    return df


def read_csv(path: str, delimiter: str, clean: bool) -> pd.DataFrame:
    """Read every field as text, optionally cleaned, and normalize the header names."""
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    if clean:
        logging.debug("Replacing %d vertical tab characters", text.count("\x0b"))
        text = clean_control_chars(text)
    df = pd.read_csv(
        io.StringIO(text),
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        sep=delimiter,
        quoting=csv.QUOTE_MINIMAL,
        engine="python",
    )
    # Drop a BOM and surrounding whitespace so the header matches the names given on the command line.
    df.columns = df.columns.str.replace("﻿", "").str.strip()
    logging.debug("Column names: %s", [repr(column) for column in df.columns])
    return df


def delimiter(value: str) -> str:
    value = DELIMITER_ESCAPES.get(value, value)
    if len(value) != 1:
        raise argparse.ArgumentTypeError("the delimiter must be a single character")
    return value


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="csv-coalesce-columns",
        description="Fill one CSV column from ordered source columns, row by row.",
    )
    parser.add_argument("input", help="CSV file to read")
    parser.add_argument("output", help="CSV file to write")
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        metavar="COLUMN",
        help="column to fill (default: %(default)s)",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        metavar="COLUMN",
        help="column to fill from; repeat in order of precedence (default: %s)"
        % ", ".join(DEFAULT_SOURCES),
    )
    parser.add_argument(
        "--on-conflict",
        choices=CONFLICT_CHOICES,
        default="keep",
        help="what to do when several sources are set: keep the target, "
        "take the first set source or the last (default: %(default)s)",
    )
    parser.add_argument(
        "--delimiter",
        type=delimiter,
        default=",",
        help="field delimiter, '\\t' for tab (default: '%(default)s')",
    )
    parser.add_argument(
        "--no-clean",
        dest="clean",
        action="store_false",
        help="keep vertical tab characters instead of replacing them with a space",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log the column names, a sample before and after, and one line per changed row",
    )
    args = parser.parse_args(argv)
    if args.sources is None:
        args.sources = list(DEFAULT_SOURCES)
    if len(set(args.sources)) != len(args.sources):
        parser.error("each --source column can be given once")
    if args.target in args.sources:
        parser.error("the --target column cannot also be a --source")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.WARNING)

    df = read_csv(args.input, args.delimiter, args.clean)
    columns = [*args.sources, args.target]
    missing = [column for column in columns if column not in df.columns]
    if missing:
        logging.error("Missing expected columns: %s", missing)
        return 1
    logging.debug("Sample before:\n%s", df[columns].head().to_string())

    for label, count in count_cases(df, args.sources).items():
        print(f"Rows with {label}: {count}")
    df = coalesce_column(df, args.target, args.sources, args.on_conflict)

    logging.debug("Sample after:\n%s", df[columns].head().to_string())
    df.to_csv(args.output, index=False, sep=args.delimiter, quoting=csv.QUOTE_MINIMAL)
    logging.debug("Wrote %s", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
