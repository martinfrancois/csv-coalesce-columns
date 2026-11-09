# AGENTS

csv-coalesce-columns is a Python command-line tool that fills one CSV column from whichever of several source columns is set, row by row (see README.md).

## Checks

Run these before committing, in a virtual environment with Python 3.12 or newer. CI runs the same steps (`.github/workflows/ci.yml`):

```bash
python -m pip install -e '.[dev]'
python -m pytest
csv-coalesce-columns examples/subscribers-before.csv output.csv
cmp output.csv examples/subscribers-after.csv
python3 main.py examples/subscribers-before.csv output.csv
cmp output.csv examples/subscribers-after.csv
csv-coalesce-columns examples/orders-before.csv output.csv \
  --target created_at --source 'Ordered At' --source 'Placed At' --delimiter ';'
cmp output.csv examples/orders-after.csv
```

## Contributing for Someone Else

martinfrancois's rule for outside contributions, and for any agent working for an outside contributor: contributors shouldn't spend time on pull requests that collide with someone else's work or that he wouldn't accept. So a contribution takes one of three paths (see "Three ways to contribute" in CONTRIBUTING.md):

- Small fix (bug fix, typo, docs improvement or similar): open a pull request directly, no issue needed. If an issue for it exists, claim it first as below.
- Existing issue: check its assignees and linked pull requests, post `/take` on the issue, and start only once the assignment comes back. Never open a pull request for an issue that isn't assigned to the contributor you work for, and don't start on one that someone else holds or that an open pull request already addresses.
- New feature: open a thread in the Ideas category of GitHub Discussions. Wait until martinfrancois approves it and opens an issue, then claim that issue with `/take`. Never open a feature pull request without an approved issue assigned to your contributor.
