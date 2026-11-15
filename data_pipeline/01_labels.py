"""Step 1: build the label table (974 PRs) from the PR-MCI repo.

Alignment label comes from the master file; the 8-type MCI taxonomy comes
from the RQ2 taxonomy file (the master file's failure_type is incomplete and
uses different names). Binary flag follows the paper: misaligned = High MCI,
partial counts as Low.
"""
import io
import urllib.request

import pandas as pd

from common import CACHE, LABELS_PARQUET, MASTER_URL, TAXONOMY_URL


def fetch(url: str) -> pd.DataFrame:
    with urllib.request.urlopen(url) as r:
        return pd.read_csv(io.BytesIO(r.read()), encoding="utf-8-sig", dtype={"pr_id": "int64"})


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    master = fetch(MASTER_URL)
    tax = fetch(TAXONOMY_URL)

    # annotator_notes / failure_evidence explain the label -> leakage, so drop them.
    master = master[["pr_id", "agent", "task_type", "manual_label"]].rename(
        columns={"manual_label": "alignment"}
    )
    tax = tax[["pr_id", "failure_type"]].rename(columns={"failure_type": "mci_type"})

    df = master.merge(tax, on="pr_id", how="left", validate="one_to_one")
    df["mci_high"] = df["alignment"].eq("misaligned")

    # ---- checks against known numbers ----
    assert len(df) == 974 and df["pr_id"].is_unique, "expected 974 unique PRs"
    vc = df["alignment"].value_counts().to_dict()
    assert vc == {"aligned": 542, "partial": 167, "misaligned": 265}, vc
    assert df["mci_type"].notna().sum() == 432, df["mci_type"].notna().sum()
    assert df.loc[df["alignment"] == "aligned", "mci_type"].isna().all()
    assert df.loc[df["alignment"] != "aligned", "mci_type"].notna().all()
    assert df["mci_type"].nunique() == 8

    df.to_parquet(LABELS_PARQUET, index=False)
    print(f"wrote {LABELS_PARQUET} ({len(df)} rows)")
    print(df["alignment"].value_counts().to_string())
    print(df["mci_type"].value_counts().to_string())
    print(df["agent"].value_counts().to_string())


if __name__ == "__main__":
    main()
