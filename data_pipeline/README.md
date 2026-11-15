# PR-MCI data pipeline

Output: `../data/prmci_pairs.jsonl` — 974 lines, one PR each (labels + description + diff).

Run in order from this folder (`pip install pandas pyarrow huggingface_hub`):

```
python 01_labels.py       # PR-MCI labels (alignment + 8-type taxonomy)
python 02_pr_meta.py      # title/body/url from AIDev pull_request (pinned revision in common.py)
python 03_diffs.py        # per-file patches + commit messages (streams pr_commit_details, ~1.3 GB at v4)
python 04_build_jsonl.py  # join -> data/prmci_pairs.jsonl
python 05_validate.py     # asserts 974 PRs / label counts, prints data-quality report
```

## Record schema

| field | notes |
|---|---|
| `pr_id, pr_number, html_url, repo_url, agent, task_type` | identifiers / metadata |
| `title, body` | PR description (model input) |
| `commits[]` | `{sha, message}` (model input, cheap extra context) |
| `files[]` | `{filename, status, additions, deletions, sha, patch}`; one row per (commit, file) |
| `diff` | all non-null patches concatenated, headed `--- filename (sha8)` |
| `diff_status` | `ok`, `partial` (some patches dropped by AIDev), `empty` (commits change nothing), `no_file_rows`, `patch_unavailable` |
| `has_readable_diff` | `diff_status` is `ok` or `partial`; use to filter the evaluation subset |
| `stats` | counts, additions/deletions, `diff_chars` |
| `label` | `alignment` (aligned/partial/misaligned), `mci_high` (misaligned only, as in the paper), `mci_type` (8 types, null if aligned) |

Annotator notes / failure evidence are deliberately excluded (they explain the label = leakage).

## Things to know

- **Empty diffs are real, not missing data.** 230 PRs (215 misaligned) have commits that change nothing —
  mostly Copilot "Initial plan" commits — plus 9 with no file rows. 194 of 196 `phantom_changes` PRs are
  in this group, so a trivial "empty diff => High MCI" rule already solves most of that type.
  Report results with and without these PRs (`diff_status in {empty, no_file_rows}`).
- 211 PRs have `partial` diffs (AIDev omits patches GitHub does not return, e.g. very large files).
- 322 PRs touch the same file in several commits; patches are concatenated per commit (same as the
  original study), not netted into one diff.
- Diff size is heavy-tailed (p95 ~340k chars, max ~2.2M), so truncation/summarisation is required.
- `partial` counts as Low MCI for the binary flag (paper convention); the 3-way label is kept for other choices.
- AIDev revision is pinned to `v4` in `common.py`; `main` is v5 (7.6M PRs).

## Recommended evaluation setup (defaults chosen; change if the team disagrees)

Report every result on two sets:

| set | n | High MCI | note |
|---|---|---|---|
| **Full** (all 974) | 974 | 265 | comparable to the paper's labels |
| **Readable-diff** (`has_readable_diff`) | 733 | 41 (5.6%) | the set where an LLM actually has to read code |

A trivial rule "empty diff or no file rows => High MCI" scores P=0.937, R=0.845, F1=0.889 on the full set,
which already beats the paper's heuristic (F1 0.630). So any detector must be compared against that rule, and
the headline claim should come from the readable-diff set. Types there: understated_scope 94,
placeholder_or_incomplete 54, other_mixed 28, misleading_specifics 13, overstated_scope 9, vague 4,
intent_mismatch 3, phantom_changes 2 -> use macro-F1 and expect the rare types to be noisy.
`partial` counts as Low MCI (paper convention); also report the "partial or misaligned = High" variant.
