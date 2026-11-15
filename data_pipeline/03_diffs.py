"""Step 3: pull per-file patches and commit messages for the 974 labeled PRs.

pr_commit_details has one row per (commit sha, file). Streams the file in
small batches with column pruning and a pr_id filter, so memory stays flat.
"""
import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from common import COMMITS_PARQUET, FILES_PARQUET, HF_REPO, HF_REVISION, LABELS_PARQUET

FILE_COLS = ["pr_id", "sha", "filename", "status", "additions", "deletions", "patch"]
COMMIT_COLS = ["pr_id", "sha", "message"]


def stream(filename: str, cols: list, wanted: set) -> pd.DataFrame:
    path = hf_hub_download(HF_REPO, filename, repo_type="dataset", revision=HF_REVISION)
    pf = pq.ParquetFile(path)
    parts = []
    for batch in pf.iter_batches(batch_size=20_000, columns=cols):
        t = batch.to_pandas()
        t = t[t["pr_id"].isin(wanted)]
        if len(t):
            parts.append(t)
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    wanted = set(pd.read_parquet(LABELS_PARQUET)["pr_id"])

    files = stream("pr_commit_details.parquet", FILE_COLS, wanted)
    files.to_parquet(FILES_PARQUET, index=False)
    print(f"file rows: {len(files):,} across {files['pr_id'].nunique()} PRs "
          f"({len(wanted) - files['pr_id'].nunique()} PRs with no file rows)")
    print(f"rows with null patch: {files['patch'].isna().sum():,}")

    commits = stream("pr_commits.parquet", COMMIT_COLS, wanted)
    commits.to_parquet(COMMITS_PARQUET, index=False)
    print(f"commit rows: {len(commits):,} across {commits['pr_id'].nunique()} PRs")


if __name__ == "__main__":
    main()
