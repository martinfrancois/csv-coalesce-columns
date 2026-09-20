#!/usr/bin/env python3
import sys
import csv
import logging
import pandas as pd

def clean_control_chars(inp_path: str, out_path: str) -> None:
    """
    Replace any vertical-tab or stray control characters so pandas
    never splits a logical record across lines.
    """
    with open(inp_path, 'r', encoding='utf-8', newline='') as fin, \
            open(out_path, 'w', encoding='utf-8', newline='\n') as fout:
        for line in fin:
            fout.write(line.replace('\x0b', ' '))

def adjust_created_at(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize header names (drop BOM, strip whitespace)
    df.columns = df.columns.str.replace('\ufeff', '').str.strip()
    logging.debug("Normalized column names: %s", df.columns.tolist())

    # Build masks
    sub_mask   = df['Subscribed'].str.strip().ne('')
    join_mask  = df['Joined'].str.strip().ne('')
    both_mask  = sub_mask & join_mask

    logging.warning("Rows where only Subscribed is non-empty: %d", int((sub_mask & ~join_mask).sum()))
    logging.warning("Rows where only Joined    is non-empty: %d", int((join_mask & ~sub_mask).sum()))
    logging.warning("Rows where BOTH are non-empty     : %d", int(both_mask.sum()))

    def pick(row):
        s = row['Subscribed'].strip()
        j = row['Joined'].strip()
        old = row['createdAt']
        if s and not j:
            logging.debug("Row %d: setting createdAt %r → %r (Subscribed)", row.name, old, s)
            return s
        if j and not s:
            logging.debug("Row %d: setting createdAt %r → %r (Joined)", row.name, old, j)
            return j
        # both or neither → leave unchanged
        return old

    df['createdAt'] = df.apply(pick, axis=1)
    return df

def main(input_csv: str, output_csv: str):
    # Show ALL DEBUG+WARNING messages
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    # Step 1: clean control chars
    tmp = input_csv + '.cleaned'
    logging.debug("Cleaning control characters into %s", tmp)
    clean_control_chars(input_csv, tmp)

    # Step 2: read everything as raw text
    logging.debug("Reading cleaned CSV")
    df = pd.read_csv(
        tmp,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        sep=',',
        quoting=csv.QUOTE_MINIMAL,
        engine='python'
    )

    # Debug: what columns did we actually get?
    logging.debug("Raw column names (repr): %s", [repr(c) for c in df.columns])
    # Debug: show first 5 rows of the relevant fields
    if all(col in df.columns for col in ('Subscribed','Joined','createdAt')):
        sample = df[['Subscribed','Joined','createdAt']].head(5)
        logging.debug("Sample before adjustment:\n%s", sample.to_string(index=True))
    else:
        missing = [c for c in ('Subscribed','Joined','createdAt') if c not in df.columns]
        logging.error("Missing expected columns: %s", missing)
        sys.exit(1)

    # Step 3: adjust createdAt per your rules
    df = adjust_created_at(df)

    # Step 4: show a sample after adjustment
    sample_after = df[['Subscribed','Joined','createdAt']].head(5)
    logging.debug("Sample after adjustment:\n%s", sample_after.to_string(index=True))

    # Step 5: write out
    df.to_csv(output_csv, index=False, quoting=csv.QUOTE_MINIMAL)
    logging.info("Wrote updated CSV to %s", output_csv)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 main.py <input.csv> <output.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
