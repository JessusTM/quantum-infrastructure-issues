"""Assemble issue records and retain collection completeness diagnostics."""

from collections import defaultdict
from pathlib import Path

from .github import GitHubClient, RepositoryReader, api_url
from .storage import parse_time, utc_now, write_json


def check_comments(reader: RepositoryReader, repository: str, issue: dict, comments: list[dict]) -> tuple[dict, list[dict], dict]:
    """Recheck mismatched counts and retain failures as explicit diagnostics."""
    if len(comments) == issue["comments"]:
        return issue, comments, {"rechecked_individually": False}
    diagnostic = {"rechecked_individually": True, "original_expected_comments": issue["comments"]}
    try:
        individual = reader.issue_comments(repository, issue["number"])
        current = reader.client.get(api_url(f"/repos/{repository}/issues/{issue['number']}"))
        if current["id"] != issue["id"]:
            raise RuntimeError("The issue ID changed during the count check.")
    except (OSError, ValueError, RuntimeError) as error:
        diagnostic["recheck_error"] = str(error)
        return issue, comments, diagnostic
    diagnostic.update({"expected_comments_on_recheck": current["comments"],
                       "individual_comments_received": len(individual),
                       "discrepancy_persists": len(individual) != current["comments"]})
    return current, individual, diagnostic


def make_record(repository: str, issue: dict, comments: list[dict], cutoff: str, diagnostic: dict) -> dict:
    """Retain comments created before the cutoff and flag later updates."""
    end = parse_time(cutoff)
    retained = sorted((comment for comment in comments if parse_time(comment["created_at"]) <= end),
                      key=lambda comment: (comment["created_at"], comment["id"]))
    updated = parse_time(issue["updated_at"]) > end or any(parse_time(c["updated_at"]) > end for c in retained)
    return {"repository": repository, "issue": issue, "comments": retained,
            "extraction": {"complete": len(comments) == issue["comments"],
                           "expected_comments_at_issue_fetch": issue["comments"],
                           "retrieved_comments_before_cutoff": len(retained),
                           "retrieved_comments_total": len(comments),
                           "updated_after_cutoff": updated, **diagnostic}}


def collect_repository(reader: RepositoryReader, repository: str, config: dict) -> tuple[list[dict], dict]:
    """Collect one repository and attach its metadata and activity evidence."""
    metadata = reader.client.get(api_url(f"/repos/{repository}"))
    commits = reader.client.get(api_url(f"/repos/{repository}/commits",
                               {"since": config["start"], "until": config["cutoff"], "per_page": 1}))
    report = {"repository": repository, "repository_id": metadata["id"],
              "language": metadata.get("language"), "stars_at_collection": metadata["stargazers_count"],
              "default_branch": metadata["default_branch"],
              "license": (metadata.get("license") or {}).get("spdx_id"), "archived": metadata["archived"],
              "commit_in_period": commits[0]["sha"] if commits else None,
              "commit_date": commits[0]["commit"]["committer"]["date"] if commits else None}
    issues, search_report = reader.issues(repository, config["start"], config["cutoff"])
    report.update(search_report)
    comments, duplicates = reader.comments(repository, config["start"])
    report.update({"comments_query_complete": True, "duplicate_comments_removed": duplicates,
                   "comments_fetched_all_issues_and_PRs": len(comments)})
    by_issue: dict[int, list] = defaultdict(list)
    for comment in comments:
        number = int(comment["issue_url"].rstrip("/").split("/")[-1])
        by_issue[number].append(comment)
    records = []
    for issue in issues:
        current, received, diagnostic = check_comments(reader, repository, issue, by_issue[issue["number"]])
        records.append(make_record(repository, current, received, config["cutoff"], diagnostic))
    complete = sum(record["extraction"]["complete"] for record in records)
    report.update({"complete_issues": complete, "incomplete_issues": len(records) - complete})
    return records, report


def collect(config: dict, data_directory: Path, offline: bool = False) -> int:
    """Save a collection snapshot; return one when extraction needs review."""
    data_directory.mkdir(parents=True, exist_ok=True)
    write_json(data_directory / "config_used.json", config)
    client = GitHubClient(data_directory, offline)
    reader = RepositoryReader(client)
    records, reports, errors = [], [], []
    for repository in config["repositories"]:
        print(f"Collecting {repository}", flush=True)
        try:
            repository_records, report = collect_repository(reader, repository, config)
        except (OSError, ValueError, RuntimeError) as error:
            report = {"repository": repository, "search_complete": False,
                      "comments_query_complete": False, "error": str(error)}
            errors.append({"repository": repository, "error": str(error)})
            reports.append(report)
            continue
        records.extend(repository_records)
        reports.append(report)
    records.sort(key=lambda record: (record["repository"].lower(), record["issue"]["number"]))
    complete = not errors and all(report.get("incomplete_issues", 0) == 0 for report in reports)
    write_json(data_directory / "issues.json", records)
    write_json(data_directory / "collection_report.json", {
        "start": config["start"], "cutoff": config["cutoff"], "processing_finished_at": utc_now(),
        "repositories": reports, "errors": errors, "complete": complete, "requests_used": client.requests})
    return 0 if complete else 1
