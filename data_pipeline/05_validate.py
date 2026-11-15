"""Step 5: sanity-check the JSONL and print a data-quality report."""
import json
from collections import Counter

import pandas as pd

from common import OUT


def main() -> None:
    recs = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    assert len(recs) == 974, len(recs)
    assert len({r["pr_id"] for r in recs}) == 974
    assert Counter(r["label"]["alignment"] for r in recs) == {"aligned": 542, "partial": 167, "misaligned": 265}
    assert sum(r["label"]["mci_type"] is not None for r in recs) == 432
    assert all(r["title"] is not None for r in recs)
    print("OK: 974 unique PRs, label/type counts match the PR-MCI release\n")

    df = pd.json_normalize(recs)
    s = "stats."
    no_diff = df[df[s + "diff_chars"] == 0]
    partial_missing = df[(df[s + "n_missing_patch"] > 0) & (df[s + "diff_chars"] > 0)]
    print(f"PRs with NO usable diff (no patch text):       {len(no_diff)}")
    print(f"PRs with diff but >=1 missing patch:           {len(partial_missing)}")
    print(f"PRs with repeated file across commits:         {(df[s+'n_repeat_file_rows'] > 0).sum()}")
    print(f"PRs with empty body:                           {(df['body'].fillna('').str.strip() == '').sum()}")
    print("\ndiff_chars quantiles:")
    print(df[s + "diff_chars"].quantile([.5, .75, .9, .95, .99, 1]).round(0).to_string())
    print("\nlabel x has-diff:")
    df["has_diff"] = df[s + "diff_chars"] > 0
    print(pd.crosstab(df["label.alignment"], df["has_diff"]).to_string())
    print("\ndiff_status x alignment:")
    print(pd.crosstab(df["diff_status"], df["label.alignment"]).to_string())
    print("\ndiff_status x mci_type (non-aligned only):")
    print(pd.crosstab(df["label.mci_type"].fillna("-"), df["diff_status"]).to_string())
    print("\nno-diff PRs by agent:")
    print(no_diff["agent"].value_counts().to_string())
    print("\nfirst 10 no-diff pr_ids:", no_diff["pr_id"].head(10).tolist())


if __name__ == "__main__":
    main()
