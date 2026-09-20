import csv
import filecmp
from pathlib import Path

import pandas as pd
import pytest

import csv_coalesce_columns as tool

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def frame(subscribed, joined, created_at):
    return pd.DataFrame(
        {"Subscribed": [subscribed], "Joined": [joined], "createdAt": [created_at]},
        dtype=str,
    )


def three_sources(a, b, c, target=""):
    return pd.DataFrame({"a": [a], "b": [b], "c": [c], "t": [target]}, dtype=str)


def read_rows(path, delimiter=","):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def test_only_subscribed_fills_created_at():
    df = tool.coalesce_column(frame("2024-01-15T09:30:00Z", "", ""))
    assert df.loc[0, "createdAt"] == "2024-01-15T09:30:00Z"


def test_only_joined_fills_created_at():
    df = tool.coalesce_column(frame("", "2024-02-20T14:05:00Z", ""))
    assert df.loc[0, "createdAt"] == "2024-02-20T14:05:00Z"


def test_both_set_leaves_created_at_unchanged():
    df = tool.coalesce_column(
        frame("2024-03-01T08:00:00Z", "2024-03-02T10:00:00Z", "2023-12-31T00:00:00Z")
    )
    assert df.loc[0, "createdAt"] == "2023-12-31T00:00:00Z"


def test_neither_set_leaves_created_at_unchanged():
    assert tool.coalesce_column(frame("", "", "")).loc[0, "createdAt"] == ""
    assert (
        tool.coalesce_column(frame("", "", "2024-04-10T12:00:00Z")).loc[0, "createdAt"]
        == "2024-04-10T12:00:00Z"
    )


def test_whitespace_only_counts_as_empty():
    df = tool.coalesce_column(frame("  ", "2024-02-20T14:05:00Z", ""))
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

    assert tool.main([str(source), str(target)]) == 0

    rows = read_rows(target)
    assert len(rows) == 1
    assert rows[0]["name"] == "Frank Example"
    assert rows[0]["createdAt"] == "2024-05-05T05:05:05Z"


def test_documented_example_matches_the_committed_after_file(tmp_path):
    target = tmp_path / "subscribers-after.csv"

    assert tool.main([str(EXAMPLES / "subscribers-before.csv"), str(target)]) == 0

    assert filecmp.cmp(target, EXAMPLES / "subscribers-after.csv", shallow=False)


def test_first_takes_the_earliest_set_source_on_conflict():
    df = tool.coalesce_column(frame("2024-03-01", "2024-03-02", "old"), on_conflict="first")
    assert df.loc[0, "createdAt"] == "2024-03-01"


def test_last_takes_the_latest_set_source_on_conflict():
    df = tool.coalesce_column(frame("2024-03-01", "2024-03-02", "old"), on_conflict="last")
    assert df.loc[0, "createdAt"] == "2024-03-02"


def test_three_sources_fill_the_target_from_the_only_set_one():
    sources = ["a", "b", "c"]
    assert tool.coalesce_column(three_sources("", "B", ""), "t", sources).loc[0, "t"] == "B"
    assert tool.coalesce_column(three_sources("", "", "C"), "t", sources).loc[0, "t"] == "C"


def test_three_sources_follow_the_given_order_on_conflict():
    sources = ["a", "b", "c"]
    first = tool.coalesce_column(three_sources("", "B", "C"), "t", sources, "first")
    assert first.loc[0, "t"] == "B"
    last = tool.coalesce_column(three_sources("A", "B", ""), "t", sources, "last")
    assert last.loc[0, "t"] == "B"
    kept = tool.coalesce_column(three_sources("A", "", "C", "old"), "t", sources, "keep")
    assert kept.loc[0, "t"] == "old"


def test_source_order_comes_from_the_command_line():
    sources = ["c", "a"]
    df = tool.coalesce_column(three_sources("A", "", "C"), "t", sources, "first")
    assert df.loc[0, "t"] == "C"


def test_unknown_conflict_policy_is_rejected():
    with pytest.raises(ValueError):
        tool.coalesce_column(frame("", "", ""), on_conflict="newest")


def test_count_cases_reports_one_count_per_source_and_one_for_conflicts():
    df = pd.DataFrame(
        {"a": ["A", "", "A", ""], "b": ["", "B", "B", ""], "t": ["", "", "", ""]}, dtype=str
    )
    assert tool.count_cases(df, ["a", "b"]) == {
        "only a set": 1,
        "only b set": 1,
        "more than one source set": 1,
    }


def test_custom_delimiter_is_used_for_reading_and_writing(tmp_path):
    source = tmp_path / "in.csv"
    target = tmp_path / "out.csv"
    source.write_text(
        "id;Ordered At;Placed At;created_at\n1;2024-06-01;;\n2;;2024-06-02;\n",
        encoding="utf-8",
        newline="",
    )

    assert (
        tool.main(
            [
                str(source),
                str(target),
                "--target",
                "created_at",
                "--source",
                "Ordered At",
                "--source",
                "Placed At",
                "--delimiter",
                ";",
            ]
        )
        == 0
    )

    assert target.read_text(encoding="utf-8").splitlines()[0] == "id;Ordered At;Placed At;created_at"
    rows = read_rows(target, delimiter=";")
    assert [row["created_at"] for row in rows] == ["2024-06-01", "2024-06-02"]


def test_tab_delimiter_can_be_given_as_backslash_t(tmp_path):
    source = tmp_path / "in.tsv"
    target = tmp_path / "out.tsv"
    source.write_text("Subscribed\tJoined\tcreatedAt\n2024-01-01\t\t\n", encoding="utf-8", newline="")

    assert tool.main([str(source), str(target), "--delimiter", "\\t"]) == 0

    assert target.read_text(encoding="utf-8") == "Subscribed\tJoined\tcreatedAt\n2024-01-01\t\t2024-01-01\n"


def test_no_clean_keeps_the_vertical_tab(tmp_path):
    source = tmp_path / "in.csv"
    target = tmp_path / "out.csv"
    source.write_text(
        'name,Subscribed,Joined,createdAt\n"Frank\x0bExample",2024-05-05,,\n',
        encoding="utf-8",
        newline="",
    )

    assert tool.main([str(source), str(target), "--no-clean"]) == 0

    rows = read_rows(target)
    assert rows[0]["name"] == "Frank\x0bExample"
    assert rows[0]["createdAt"] == "2024-05-05"


def test_missing_columns_exit_with_status_one(tmp_path, caplog):
    source = tmp_path / "in.csv"
    source.write_text("email,Subscribed\nuser1@example.com,2024-01-01\n", encoding="utf-8")

    assert tool.main([str(source), str(tmp_path / "out.csv")]) == 1

    assert "Missing expected columns: ['Joined', 'createdAt']" in caplog.text


def test_target_cannot_be_a_source():
    with pytest.raises(SystemExit):
        tool.parse_args(["in.csv", "out.csv", "--target", "a", "--source", "a"])


def test_generic_example_matches_the_committed_after_file(tmp_path):
    target = tmp_path / "orders-after.csv"

    assert (
        tool.main(
            [
                str(EXAMPLES / "orders-before.csv"),
                str(target),
                "--target",
                "created_at",
                "--source",
                "Ordered At",
                "--source",
                "Placed At",
                "--delimiter",
                ";",
            ]
        )
        == 0
    )

    assert filecmp.cmp(target, EXAMPLES / "orders-after.csv", shallow=False)
