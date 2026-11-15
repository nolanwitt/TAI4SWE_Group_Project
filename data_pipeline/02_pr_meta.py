"""Step 2: pull PR title/body/url for the 974 labeled PRs from AIDev.

Streams all_pull_request (6.7 GB) with column pruning + a pr_id filter so only
matching rows are materialised. Downloads the file once into the HF cache.
"""
import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from common import HF_REPO, HF_REVISION, LABELS_PARQUET, META_PARQUET

COLS = ["id", "number", "title", "body", "html_url", "repo_url", "agent"]


def scan(filename: str, wanted: set) -> pd.DataFrame:
    path = hf_hub_download(HF_REPO, filename, repo_type="dataset", revision=HF_REVISION)
    print("using", path)
    pf = pq.ParquetFile(path)
    parts = []
    for batch in pf.iter_batches(batch_size=65_536, columns=COLS):
        t = batch.to_pandas()
        t = t[t["id"].isin(wanted)]
        if len(t):
            parts.append(t)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=COLS)


def main() -> None:
    ids = pd.read_parquet(LABELS_PARQUET)["pr_id"].tolist()
    wanted = set(ids)

    # Small AIDev-pop table first (362 MB); the 6.7 GB all_pull_request only
    # if some ids are not in it.
    found = scan("pull_request.parquet", wanted)
    rest = wanted - set(found["id"])
    print(f"pull_request (pop): {len(found)} found, {len(rest)} remaining")
    if rest:
        found = pd.concat([found, scan("all_pull_request.parquet", rest)], ignore_index=True)

    meta = found.drop_duplicates("id").rename(columns={"id": "pr_id", "agent": "agent_aidev"})

    missing = wanted - set(meta["pr_id"])
    print(f"found {len(meta)}/{len(ids)}; missing {len(missing)}")
    if missing:
        print("missing ids (first 20):", sorted(missing)[:20])
    meta.to_parquet(META_PARQUET, index=False)
    print("wrote", META_PARQUET)


if __name__ == "__main__":
    main()
