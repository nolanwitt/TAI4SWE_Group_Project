"""Shared constants for the PR-MCI data pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data_pipeline" / "cache"
OUT = ROOT / "data" / "prmci_pairs.jsonl"

PRMCI_RAW = "https://raw.githubusercontent.com/gjz78910/PR-MCI/main"
MASTER_URL = f"{PRMCI_RAW}/results/all_annotations_with_taxonomy.csv"
TAXONOMY_URL = f"{PRMCI_RAW}/data/manual_annotations_rq2_taxonomy.csv"

HF_REPO = "hao-li/AIDev"
# Pin the AIDev release for reproducibility. "v4" matches the proposal;
# "main" is v5 (7.6M PRs). Change here only.
HF_REVISION = "v4"

LABELS_PARQUET = CACHE / "labels.parquet"
META_PARQUET = CACHE / "pr_meta.parquet"
FILES_PARQUET = CACHE / "pr_files.parquet"
COMMITS_PARQUET = CACHE / "pr_commits.parquet"
