"""Access GitHub REST endpoints with caching and explicit pagination checks."""

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .storage import parse_time, read_json, utc_now, write_json

API_URL = "https://api.github.com"


def api_url(path: str, parameters: dict | None = None) -> str:
    """Build a URL for a public GitHub REST endpoint."""
    url = API_URL + path
    if parameters:
        url += "?" + urllib.parse.urlencode(parameters)
    return url


class GitHubClient:
    """Retrieve JSON responses and retain their provenance in a local cache."""

    def __init__(self, data_directory: Path, offline: bool = False) -> None:
        """Load an existing cache index without making network requests."""
        self.root = data_directory
        self.index_path = data_directory / "cache_index.json"
        self.index = read_json(self.index_path) if self.index_path.exists() else {}
        self.offline = offline
        self.requests: list[dict] = []

    def get(self, url: str) -> Any:
        """Return a cached response or retrieve and persist an uncached one."""
        if not url.startswith(API_URL + "/"):
            raise ValueError("Only public GitHub API URLs are supported.")
        if url in self.index:
            entry = self.index[url]
            self.requests.append({"url": url, "cached": True, **entry})
            return read_json(self.root / entry["file"])
        if self.offline:
            raise RuntimeError(f"No cached response is available for {url}")
        payload, headers = self._request(url)
        relative_path = "cache/" + hashlib.sha256(url.encode()).hexdigest() + ".json"
        write_json(self.root / relative_path, payload)
        entry = {"file": relative_path, "retrieved_at": utc_now(),
                 "source": "python_urllib_github_rest", "response_headers": headers}
        self.index[url] = entry
        write_json(self.index_path, self.index)
        self.requests.append({"url": url, "cached": False, **entry})
        return payload

    def _request(self, url: str) -> tuple[Any, dict]:
        """Retry transient failures up to three times; surface access limits."""
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "HQC-issues-study"}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(url, headers=headers)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.load(response)
                    names = ("Link", "ETag", "Date", "X-RateLimit-Remaining")
                    response_headers = {name: response.headers[name] for name in names if name in response.headers}
                return payload, response_headers
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == 2:
                    raise RuntimeError(f"GitHub returned HTTP {error.code} for {url}") from error
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == 2:
                    raise RuntimeError(f"GitHub request failed for {url}: {error}") from error
            time.sleep(2 ** attempt)
        raise RuntimeError(f"GitHub request retries were exhausted for {url}")


class RepositoryReader:
    """Retrieve repository issues and comments with deterministic deduplication."""

    def __init__(self, client: GitHubClient) -> None:
        """Use an injected client for online collection or offline replay."""
        self.client = client

    def issues(self, repository: str, start: str, cutoff: str) -> tuple[list[dict], dict]:
        """Fetch every search page, reject truncated searches, and exclude PRs."""
        query = f"repo:{repository} is:issue created:{start[:10]}..{cutoff[:10]}"
        found: dict[int, dict] = {}
        duplicates = 0
        total = None
        page = 1
        while True:
            parameters = {"q": query, "per_page": 100, "sort": "created", "order": "asc", "page": page}
            response = self.client.get(api_url("/search/issues", parameters))
            if response.get("incomplete_results"):
                raise RuntimeError(f"GitHub returned incomplete search results for {repository}.")
            count = response["total_count"]
            if count > 1000:
                raise RuntimeError(f"Split the period: {repository} exceeds GitHub's 1,000-result search limit.")
            if total is not None and total != count:
                raise RuntimeError(f"The search total changed while collecting {repository}.")
            total = count
            for issue in response["items"]:
                duplicates += int(issue["id"] in found)
                found[issue["id"]] = issue
            if len(response["items"]) < 100 or page * 100 >= total:
                break
            page += 1
        if len(found) != total:
            raise RuntimeError(f"Expected {total} unique results, received {len(found)} for {repository}.")
        selected = [issue for issue in found.values() if "pull_request" not in issue
                    and parse_time(start) <= parse_time(issue["created_at"]) <= parse_time(cutoff)]
        return selected, {"search_total": total, "issues_in_period": len(selected),
                          "duplicate_issues_removed": duplicates, "search_complete": True, "query": query}

    def _comment_pages(self, path: str, parameters: dict) -> tuple[list[dict], int]:
        """Follow numbered comment pages and deduplicate by comment ID."""
        found: dict[int, dict] = {}
        duplicates = 0
        page = 1
        while True:
            rows = self.client.get(api_url(path, {**parameters, "per_page": 100, "page": page}))
            if not isinstance(rows, list):
                raise RuntimeError(f"Unexpected comment response for {path}.")
            for comment in rows:
                duplicates += int(comment["id"] in found)
                found[comment["id"]] = comment
            if len(rows) < 100:
                return list(found.values()), duplicates
            page += 1

    def comments(self, repository: str, start: str) -> tuple[list[dict], int]:
        """Fetch repository-wide comments; GitHub's since parameter filters updates."""
        return self._comment_pages(f"/repos/{repository}/issues/comments",
                                   {"since": start, "sort": "created", "direction": "asc"})

    def issue_comments(self, repository: str, number: int) -> list[dict]:
        """Fetch one issue's comments for an independent count check."""
        comments, _ = self._comment_pages(f"/repos/{repository}/issues/{number}/comments", {})
        return comments
