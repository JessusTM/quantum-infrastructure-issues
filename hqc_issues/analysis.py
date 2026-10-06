"""Apply the observation period and keyword rules to a retained snapshot."""

import hashlib
import re
from collections import Counter
from pathlib import Path

from .storage import parse_time, read_json, utc_now, write_csv, write_json

REVIEW_FIELDS = [
    "repository", "issue_number", "url", "created_at", "state_observed", "title", "body",
    "comments_count", "comments_text", "extraction_complete", "updated_after_cutoff",
    "matched_keywords", "selected_for_sample", "pertinent", "eligibility_reason",
    "rq1_problem_or_constraint", "rq2_reported_software_effect", "rq3_information_types",
    "evidence_fragments_and_locations", "reviewer", "review_date",
]
CARD_FIELDS = [
    "card_id", "repository", "issue_number", "rq", "idea", "group",
    "evidence_location", "evidence_fragment",
]


def filter_period(records: list[dict], config: dict) -> list[dict]:
    """Filter creation timestamps without altering the original snapshot."""
    start, cutoff = parse_time(config["start"]), parse_time(config["cutoff"])
    selected = []
    for record in records:
        issue = record["issue"]
        if record["repository"] not in config["repositories"] or "pull_request" in issue:
            continue
        if not start <= parse_time(issue["created_at"]) <= cutoff:
            continue
        comments = [comment for comment in record["comments"] if parse_time(comment["created_at"]) <= cutoff]
        updated = parse_time(issue["updated_at"]) > cutoff or any(parse_time(c["updated_at"]) > cutoff for c in comments)
        extraction = {**record["extraction"], "retrieved_comments_before_cutoff": len(comments),
                      "updated_after_cutoff": updated}
        selected.append({**record, "comments": comments, "extraction": extraction})
    return sorted(selected, key=lambda record: (record["repository"].lower(), record["issue"]["number"]))


def compile_keywords(keywords: list[str]) -> list[tuple[str, re.Pattern]]:
    """Match case-insensitively with word boundaries and separator variants."""
    patterns = []
    for keyword in keywords:
        parts = re.split(r"[\s_-]+", keyword.strip())
        expression = r"(?<![a-z0-9])" + r"[\s_-]+".join(re.escape(part) for part in parts) + r"(?![a-z0-9])"
        patterns.append((keyword, re.compile(expression, re.IGNORECASE)))
    return patterns


def keyword_matches(record: dict, patterns: list[tuple[str, re.Pattern]]) -> list[dict]:
    """Locate candidate keywords in the title, body, and retained comments."""
    issue = record["issue"]
    units = [("title", issue["title"]), ("body", issue.get("body") or "")]
    units.extend((f"comment:{comment['id']}", comment.get("body") or "") for comment in record["comments"])
    return [{"keyword": keyword, "location": location}
            for keyword, pattern in patterns for location, text in units if pattern.search(text)]


def review_row(candidate: dict, selected: bool = False) -> dict:
    """Export one candidate with blank human eligibility and coding fields."""
    issue = candidate["issue"]
    row = {field: "" for field in REVIEW_FIELDS}
    comment_text = "\n\n".join(
        f"[Comment {comment['id']} | {comment['created_at']} | {comment.get('html_url', '')}]\n{comment.get('body') or ''}"
        for comment in candidate["comments"])
    row.update({
        "repository": candidate["repository"], "issue_number": issue["number"],
        "url": issue["html_url"], "created_at": issue["created_at"], "state_observed": issue["state"],
        "title": issue["title"], "body": issue.get("body") or "",
        "comments_count": len(candidate["comments"]), "comments_text": comment_text,
        "extraction_complete": candidate["extraction"]["complete"],
        "updated_after_cutoff": candidate["extraction"]["updated_after_cutoff"],
        "matched_keywords": "; ".join(sorted({hit["keyword"] for hit in candidate["keyword_matches"]})),
        "selected_for_sample": selected})
    return row


def check_snapshot_period(config: dict, collection_report: dict) -> None:
    """Reject an analysis period extending beyond the retained collection."""
    if parse_time(config["start"]) < parse_time(collection_report["start"]):
        raise ValueError("The analysis starts before the retained collection.")
    if parse_time(config["cutoff"]) > parse_time(collection_report["cutoff"]):
        raise ValueError("The analysis cutoff exceeds the retained collection.")


def check_existing_analysis(config: dict, output_directory: Path) -> None:
    """Require a new directory when analysis inputs would invalidate review files."""
    config_path = output_directory / "analysis_config.json"
    if not config_path.exists():
        return
    existing = read_json(config_path)
    fields = ("repositories", "start", "cutoff", "keywords", "sampling")
    if any(existing.get(field) != config.get(field) for field in fields):
        raise ValueError("The analysis configuration changed; use a new output directory.")


def load_review_annotations(config: dict, data_directory: Path, candidates_path: Path) -> dict:
    """Load recorded preliminary coding only for its exact source snapshot."""
    path = data_directory / "review_annotations.json"
    if not path.exists():
        return {}
    annotations = read_json(path)
    checksum = hashlib.sha256(candidates_path.read_bytes()).hexdigest()
    expected_seed = config.get("sampling", {}).get("seed")
    matches = (annotations["analysis_cutoff"] == config["cutoff"]
               and annotations["sampling_seed"] == expected_seed
               and annotations["candidates_sha256"] == checksum)
    return annotations if matches else {}


def add_annotation(row: dict, annotation: dict) -> dict:
    """Apply recorded coding without inventing a reviewer or a review date."""
    fields = ("pertinent", "eligibility_reason", "rq1_problem_or_constraint",
              "rq2_reported_software_effect", "rq3_information_types", "evidence_fragments_and_locations")
    row.update({field: annotation.get(field, "") for field in fields})
    return row


def export_review_files(candidates: list[dict], annotations: dict, output_directory: Path) -> None:
    """Create two review CSVs and preserve them on subsequent executions."""
    review_path = output_directory / "manual_review.csv"
    annotation_index = {(row["repository"], int(row["issue_number"])): row
                        for row in annotations.get("issues", [])}
    if not review_path.exists():
        rows = [add_annotation(review_row(candidate),
                              annotation_index.get((candidate["repository"], candidate["issue"]["number"]), {}))
                for candidate in candidates]
        write_csv(review_path, rows, REVIEW_FIELDS)
    cards_path = output_directory / "cards_proposed.csv"
    if not cards_path.exists():
        write_csv(cards_path, annotations.get("cards", []), CARD_FIELDS)


def analyze(config: dict, data_directory: Path, output_directory: Path) -> dict:
    """Generate candidate and review artifacts; do not perform classification."""
    check_existing_analysis(config, output_directory)
    source_report = read_json(data_directory / "collection_report.json")
    check_snapshot_period(config, source_report)
    records = filter_period(read_json(data_directory / "issues.json"), config)
    patterns = compile_keywords(config["keywords"])
    candidates = []
    for record in records:
        matches = keyword_matches(record, patterns)
        if matches:
            candidates.append({**record, "keyword_matches": matches})
    issue_counts = Counter(record["repository"] for record in records)
    comment_counts = Counter()
    for record in records:
        comment_counts[record["repository"]] += len(record["comments"])
    candidate_counts = Counter(record["repository"] for record in candidates)
    complete_counts = Counter(record["repository"] for record in candidates if record["extraction"]["complete"])
    incomplete_counts = Counter(record["repository"] for record in records if not record["extraction"]["complete"])
    metadata = {row["repository"]: row for row in source_report["repositories"]}
    activity_path = data_directory / "repository_activity_evidence.json"
    if activity_path.exists():
        activity = read_json(activity_path)
        if activity["cutoff"] == config["cutoff"] and activity["start"] == config["start"]:
            for row in activity["repositories"]:
                metadata[row["repository"]] = {**metadata[row["repository"]], **row}
    summary = []
    for repository in config["repositories"]:
        source = metadata[repository]
        summary.append({
            "repository": repository, "stars_at_collection": source.get("stars_at_collection"),
            "commit_date": source.get("commit_date"), "issues_in_period": issue_counts[repository],
            "comments_in_period": comment_counts[repository], "keyword_candidates": candidate_counts[repository],
            "complete_candidates": complete_counts[repository], "incomplete_issues": incomplete_counts[repository],
            "collection_complete": source.get("search_complete", False)
            and source.get("comments_query_complete", False) and not incomplete_counts[repository],
            "error": source.get("error", "")})
    totals = {"issues": len(records), "comments": sum(comment_counts.values()),
              "keyword_candidates": len(candidates), "complete_candidates": sum(complete_counts.values()),
              "incomplete_issues": sum(incomplete_counts.values())}
    candidates_path = output_directory / "candidates.json"
    if candidates_path.exists() and (output_directory / "manual_review.csv").exists():
        if read_json(candidates_path) != candidates:
            raise ValueError("The candidate data changed; use a new output directory to preserve review decisions.")
    write_json(output_directory / "analysis_config.json", config)
    write_json(output_directory / "period_issues.json", records)
    write_json(output_directory / "candidates.json", candidates)
    annotations = load_review_annotations(config, data_directory, candidates_path)
    coded = annotations.get("issues", [])
    write_json(output_directory / "summary.json", {"repositories": summary, "totals": totals,
               "analysis_start": config["start"], "analysis_cutoff": config["cutoff"],
               "processed_at": utc_now(), "source_collection_cutoff": source_report["cutoff"],
               "keywords_are_not_classifications": True,
               "preliminary_coding": {"included": sum(row["pertinent"] == "yes" for row in coded),
                                      "excluded": sum(row["pertinent"] == "no" for row in coded),
                                      "assistance": "AI-assisted suggestions and conservative eligibility review"}})
    export_review_files(candidates, annotations, output_directory)
    return totals
