import csv
import filecmp
from pathlib import Path

import pandas as pd

import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def frame(subscribed, joined, created_at):
    return pd.DataFrame(
        {"Subscribed": [subscribed], "Joined": [joined], "createdAt": [created_at]},
        dtype=str,
    )


def test_only_subscribed_fills_created_at():
    df = main.adjust_created_at(frame("2024-01-15T09:30:00Z", "", ""))
    assert df.loc[0, "createdAt"] == "2024-01-15T09:30:00Z"


def test_only_joined_fills_created_at():
    df = main.adjust_created_at(frame("", "2024-02-20T14:05:00Z", ""))
    assert df.loc[0, "createdAt"] == "2024-02-20T14:05:00Z"


def test_both_set_leaves_created_at_unchanged():
    df = main.adjust_created_at(
        frame("2024-03-01T08:00:00Z", "2024-03-02T10:00:00Z", "2023-12-31T00:00:00Z")
    )
    assert df.loc[0, "createdAt"] == "2023-12-31T00:00:00Z"


def test_neither_set_leaves_created_at_unchanged():
    assert main.adjust_created_at(frame("", "", "")).loc[0, "createdAt"] == ""
    assert (
        main.adjust_created_at(frame("", "", "2024-04-10T12:00:00Z")).loc[0, "createdAt"]
        == "2024-04-10T12:00:00Z"
    )


def test_whitespace_only_counts_as_empty():
    df = main.adjust_created_at(frame("  ", "2024-02-20T14:05:00Z", ""))
    assert df.loc[0, "createdAt"] == "2024-02-20T14:05:00Z"


def test_vertical_tab_inside_a_field_is_replaced_and_the_row_stays_whole(tmp_path):
    source = tmp_path / "in.csv"
    target = tmp_path / "out.csv"
    source.write_text(
        "email,name,Subscribed,Joined,createdAt\n"
        'user6@example.com,"Frank\x0bExample",2024-05-05T05:05:05Z,,\n',
        encoding="utf-8",
        newline="",
    )

    main.main(str(source), str(target))

    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["name"] == "Frank Example"
    assert rows[0]["createdAt"] == "2024-05-05T05:05:05Z"


def test_documented_example_matches_the_committed_after_file(tmp_path):
    source = tmp_path / "subscribers-before.csv"
    source.write_bytes((EXAMPLES / "subscribers-before.csv").read_bytes())
    target = tmp_path / "subscribers-after.csv"

    main.main(str(source), str(target))

    assert filecmp.cmp(target, EXAMPLES / "subscribers-after.csv", shallow=False)
