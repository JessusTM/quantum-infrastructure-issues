"""Validate command-line input and dispatch one pipeline stage."""

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze
from .collection import collect
from .sampling import sample
from .storage import parse_time, read_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def validate_config(config: dict) -> None:
    """Reject invalid periods, duplicate repositories, and empty keyword terms."""
    if parse_time(config["start"]) > parse_time(config["cutoff"]):
        raise ValueError("The start timestamp must precede the cutoff.")
    repositories = config["repositories"]
    if not repositories or len(set(repo.lower() for repo in repositories)) != len(repositories):
        raise ValueError("Repositories must be nonempty and unique.")
    if not config["keywords"] or any(not term.strip() for term in config["keywords"]):
        raise ValueError("Provide at least one nonempty keyword.")


def build_parser() -> argparse.ArgumentParser:
    """Describe pipeline stages and their input and output locations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "analyze", "sample"))
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config.json")
    parser.add_argument("--data", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results")
    parser.add_argument("--offline", action="store_true", help="Use retained API responses during collection.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a pipeline stage and report recoverable input or API errors."""
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        config = read_json(arguments.config)
        validate_config(config)
        if arguments.command == "collect":
            return collect(config, arguments.data, arguments.offline)
        if arguments.command == "analyze":
            result = analyze(config, arguments.data, arguments.output)
        else:
            result = sample(config, arguments.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
