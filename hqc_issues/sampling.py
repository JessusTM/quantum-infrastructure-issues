"""Select and record a reproducible random sample stratified by repository."""

import hashlib
import platform
import random
import csv
from pathlib import Path

from .storage import read_json, utc_now, write_csv, write_json


def select_sample(candidates: list[dict], repositories: list[str], per_repository: int, seed: int) -> list[dict]:
    """Draw equal counts from complete candidates using one seeded generator.

    Candidates are sorted by repository and issue number before drawing.
    Ineligible cases identified later remain part of the original draw.
    """
    if per_repository < 1:
        raise ValueError("The sample size per repository must be positive.")
    generator = random.Random(seed)
    selected = []
    for repository in sorted(repositories, key=str.lower):
        pool = sorted((candidate for candidate in candidates
                       if candidate["repository"] == repository and candidate["extraction"]["complete"]),
                      key=lambda candidate: candidate["issue"]["number"])
        if len(pool) < per_repository:
            raise ValueError(f"{repository} has {len(pool)} complete candidates; {per_repository} are required.")
        selected.extend(generator.sample(pool, per_repository))
    return sorted(selected, key=lambda candidate: (candidate["repository"].lower(), candidate["issue"]["number"]))


def candidate_id(candidate: dict) -> str:
    """Return a unique, human-readable repository and issue identifier."""
    return f"{candidate['repository']}#{candidate['issue']['number']}"


def mark_selected_cases(path: Path, candidates: list[dict], selected_ids: set[str]) -> None:
    """Update selection flags in the master CSV without changing review fields."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    row_ids = [f"{row['repository']}#{row['issue_number']}" for row in rows]
    candidate_ids = {candidate_id(candidate) for candidate in candidates}
    if len(row_ids) != len(candidate_ids) or set(row_ids) != candidate_ids:
        raise ValueError("The review CSV does not match the current candidates.")
    for row, identifier in zip(rows, row_ids):
        row["selected_for_sample"] = identifier in selected_ids
    write_csv(path, rows, fields)


def sample(config: dict, output_directory: Path) -> dict:
    """Persist the draw and mark sampled rows in the existing master CSV."""
    analysis_config = read_json(output_directory / "analysis_config.json")
    for field in ("repositories", "start", "cutoff", "keywords"):
        if analysis_config[field] != config[field]:
            raise ValueError(f"Analysis configuration differs in {field}; rerun analyze before sampling.")
    settings = config["sampling"]
    candidates = read_json(output_directory / "candidates.json")
    selected = select_sample(candidates, config["repositories"], settings["per_repository"], settings["seed"])
    selected_ids = {candidate_id(candidate) for candidate in selected}
    frame = {repository: [candidate_id(candidate)
                          for candidate in sorted(candidates, key=lambda c: c["issue"]["number"])
                          if candidate["repository"] == repository and candidate["extraction"]["complete"]]
             for repository in sorted(config["repositories"], key=str.lower)}
    manifest = {
        "method": "stratified_random_equal_allocation", "seed": settings["seed"],
        "per_repository": settings["per_repository"], "sample_size": len(selected),
        "python_version": platform.python_version(), "selected_at": utc_now(),
        "analysis_start": config["start"], "analysis_cutoff": config["cutoff"],
        "candidates_sha256": hashlib.sha256((output_directory / "candidates.json").read_bytes()).hexdigest(),
        "sampling_frame": frame, "selected_ids": sorted(selected_ids),
        "sampling_executed": True,
        "replacement_rule": "No automatic replacement after eligibility review."}
    manifest_path = output_directory / "sample_manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        keys = ("seed", "per_repository", "candidates_sha256", "selected_ids")
        if any(existing[key] != manifest[key] for key in keys):
            raise ValueError("An existing draw differs; use a new output directory to preserve it.")
        mark_selected_cases(output_directory / "manual_review.csv", candidates, selected_ids)
        return existing
    mark_selected_cases(output_directory / "manual_review.csv", candidates, selected_ids)
    write_json(manifest_path, manifest)
    write_json(output_directory / "sample.json", selected)
    return manifest
