"""Step 4: join labels + PR text + commits + file patches into one JSONL (1 line per PR)."""
import json

import pandas as pd

from common import COMMITS_PARQUET, FILES_PARQUET, LABELS_PARQUET, META_PARQUET, OUT


def nn(x):
    """NaN/None -> None, numpy scalars -> python."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    return x.item() if hasattr(x, "item") else x


def main() -> None:
    labels = pd.read_parquet(LABELS_PARQUET)
    meta = pd.read_parquet(META_PARQUET).set_index("pr_id")
    files = pd.read_parquet(FILES_PARQUET)
    commits = pd.read_parquet(COMMITS_PARQUET)

    files_by_pr = {k: g for k, g in files.groupby("pr_id", sort=False)}
    commits_by_pr = {k: g for k, g in commits.groupby("pr_id", sort=False)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        for lab in labels.sort_values("pr_id").itertuples(index=False):
            pid = lab.pr_id
            m = meta.loc[pid]
            fg = files_by_pr.get(pid)
            cg = commits_by_pr.get(pid)

            flist = []
            if fg is not None:
                for r in fg.itertuples(index=False):
                    flist.append({
                        "filename": nn(r.filename), "status": nn(r.status),
                        "additions": nn(r.additions), "deletions": nn(r.deletions),
                        "sha": nn(r.sha), "patch": nn(r.patch),
                    })
            clist = [] if cg is None else [
                {"sha": r.sha, "message": nn(r.message)} for r in cg.itertuples(index=False)
            ]

            # Flat diff: per-commit patches in stored order (same as the original study).
            diff = "\n".join(
                f"--- {f['filename']} ({f['sha'][:8] if f['sha'] else ''})\n{f['patch']}"
                for f in flist if f["patch"]
            )
            seen, dup = set(), 0
            for f in flist:
                dup += f["filename"] in seen
                seen.add(f["filename"])

            n_missing = sum(f["patch"] is None for f in flist)
            changed = sum((f["additions"] or 0) + (f["deletions"] or 0) for f in flist)
            if not flist:
                diff_status = "no_file_rows"        # PR has no recorded file changes
            elif diff:
                diff_status = "partial" if n_missing else "ok"
            elif changed == 0:
                diff_status = "empty"               # commits exist but change nothing (e.g. "Initial plan")
            else:
                diff_status = "patch_unavailable"   # lines changed, but AIDev dropped the patch text

            rec = {
                "pr_id": int(pid),
                "pr_number": nn(m["number"]),
                "html_url": nn(m["html_url"]),
                "repo_url": nn(m["repo_url"]),
                "agent": lab.agent,
                "task_type": lab.task_type,
                "title": nn(m["title"]),
                "body": nn(m["body"]),
                "commits": clist,
                "files": flist,
                "diff": diff,
                "diff_status": diff_status,
                "has_readable_diff": diff_status in ("ok", "partial"),
                "stats": {
                    "n_commits": len(clist),
                    "n_file_rows": len(flist),
                    "n_unique_files": len(seen),
                    "n_repeat_file_rows": dup,
                    "n_missing_patch": sum(f["patch"] is None for f in flist),
                    "additions": int(sum(f["additions"] or 0 for f in flist)),
                    "deletions": int(sum(f["deletions"] or 0 for f in flist)),
                    "diff_chars": len(diff),
                },
                "label": {
                    "alignment": lab.alignment,
                    "mci_high": bool(lab.mci_high),
                    "mci_type": nn(lab.mci_type),
                },
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} records to {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
