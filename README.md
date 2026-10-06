<div align="center">
  <h1><em>HQC Issues</em></h1>

  <p>
    <strong>
      A data collection and preparation artifact for studying quantum infrastructure constraints reported in GitHub issues
    </strong>
  </p>

  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 or later"></a>
    <a href="https://docs.github.com/en/rest"><img src="https://img.shields.io/badge/GitHub-REST%20API-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub REST API"></a>
    <a href="https://docs.python.org/3/library/"><img src="https://img.shields.io/badge/Dependencies-Standard%20Library-3776AB?style=for-the-badge" alt="Python standard library only"></a>
    <a href="#snapshot"><img src="https://img.shields.io/badge/Snapshot-2026--10--06-555555?style=for-the-badge" alt="Snapshot dated October 6, 2026"></a>
  </p>

  <p>
    <a href="#overview">Overview</a> ·
    <a href="#study-scope">Study Scope</a> ·
    <a href="#collection-workflow">Collection Workflow</a> ·
    <a href="#getting-started">Getting Started</a> ·
    <a href="#snapshot">Snapshot</a> ·
    <a href="#manual-review">Manual Review</a> ·
    <a href="#scope-and-limitations">Limitations</a>
  </p>
</div>

**Version 0.1.0**

## Overview

This repository contains the code, data, and preliminary analysis for *How Quantum Infrastructure Constrains Hybrid Software: An Empirical Study*.

The purpose of this advance is to test the collection and classification procedure. Ten candidates were sampled from five manually selected repositories. Applying a conservative relevance criterion leaves one issue for preliminary classification and nine exclusions. This result does not establish a complete taxonomy or the prevalence of infrastructure problems.

The qualitative coding was prepared with AI assistance and is preliminary. The CSV files retain the reasons and supporting fragments. Reviewer names and review dates are left blank rather than assigning a review that has not been recorded.

## Study Scope

The selected repositories are:

- `Qiskit/qiskit-ibm-runtime`
- `PennyLaneAI/pennylane-qiskit`
- `qiskit-community/qiskit-machine-learning`
- `amazon-braket/amazon-braket-sdk-python`
- `unitaryfoundation/mitiq`

The analysis period is **January 1, 2026, 00:00:00 UTC through October 2, 2026, 23:59:59 UTC**, inclusive. An issue is analyzed together with its title, body, and accessible comments created by the cutoff.

Repository activity and technology evidence are retained in `data/repository_activity_evidence.json` and `data/repository_technology_evidence.json`.

## Procedure

1. Query the GitHub REST API and retrieve all issue and comment pages.
2. Exclude pull requests, deduplicate identifiers, and apply the creation-date cutoff.
3. Compare comment counts and recheck discrepancies through individual endpoints. Keep unresolved cases flagged.
4. Find candidates using the vocabulary in `config.json`, across titles, bodies, and retained comments.
5. Select two candidates without extraction discrepancies from each repository.
6. Review relevance, record labels and evidence, and group text fragments into preliminary categories through an adaptation of card sorting.

Keyword matching uses an OR rule, ignores case, respects word boundaries, and treats spaces, hyphens, and underscores as equivalent. No stemming is applied. The 54-entry vocabulary was developed from the study concepts and operational terms discussed during preparation; it is not a validated dictionary.

Searches reporting incomplete results or exceeding GitHub's 1,000-result limit are rejected. The comment API's `since` parameter filters update dates, so comment creation dates are checked separately.

## Sampling

The sample contains **ten issues, two per repository**. Equal allocation was chosen to test the procedure across the five sources within the available time. It is not proportional to repository size and does not establish statistical representativeness, a confidence level, or taxonomy saturation.

The seed **`20261006`** uses the package preparation date as a fixed integer. Its value is arbitrary and has no statistical meaning. It was configured before the recorded draw and retained after reading the selected cases. No alternative seeds were compared to obtain more relevant cases.

The code uses `random.Random(seed).sample()`, sorted repository names, and candidates sorted by issue number. Reproduction requires the same input data, ordering, algorithm, and call sequence. Python **3.12.14** was used for the recorded draw. The seed, Python version, full sampling frame, checksum, and selected IDs are retained in `results/sample_manifest.json`. See [Python's reproducibility notes](https://docs.python.org/3/library/random.html#notes-on-reproducibility).

Irrelevant cases remain in the draw and are not replaced. Unselected candidates remain unclassified. Ambiguous cases are not included merely to increase the number of findings.

## Getting Started

Python **3.10 or later** is required. No third-party packages are needed.

From the repository root, reproduce the supplied inputs and preliminary coding without querying GitHub:

```bash
python3 miner.py analyze --output reproduced_results
python3 miner.py sample --output reproduced_results
```

The script generates the data columns and selection flags. It does not infer qualitative categories from keywords. Recorded preliminary coding is loaded from `data/review_annotations.json` only when the cutoff, seed, and candidate checksum match. A new dataset without matching annotations receives blank classification fields and an empty card template.

To collect current API responses, use separate directories:

```bash
python3 miner.py collect --data new_extraction
python3 miner.py analyze --data new_extraction --output new_results
python3 miner.py sample --output new_results
```

An optional GitHub token is read from `GITHUB_TOKEN` or `GH_TOKEN`. A new extraction may observe different text and counts.

The original October 6 API responses can also be replayed offline. Copy `data/cache/` and `data/cache_index.json` into a separate directory, then run `collect --offline --config data/config_used.json --data <copied-directory>`. Exit code 1 is expected for that snapshot because three comment-count discrepancies remain.

Run the tests with:

```bash
python3 -m unittest -v test_miner.py
```

## Files

Only **two CSV files** are generated:

- `results/manual_review.csv`: all 176 candidates, full text, metadata, keyword matches, extraction indicators, sample selection, relevance decisions, RQ labels, and supporting fragments. Filter `selected_for_sample` to `True` to inspect the ten sampled cases. Unsampled rows have blank classification fields.
- `results/cards_proposed.csv`: seven preliminary cards from the included issue, with one idea per card, its source, RQ, and group. Group names and definitions remain preliminary.

Other files preserve the inputs and processing record:

- `config.json`: repositories, period, keywords, and sampling settings.
- `miner.py`: command-line entry point.
- `hqc_issues/`: modules for storage, API access, collection, analysis, sampling, and CLI orchestration.
- `data/`: source issues, cached responses, collection diagnostics, repository evidence, and recorded preliminary annotations.
- `results/summary.json`: collection counts and the recorded preliminary coding summary.
- `results/sample_manifest.json`: sampling frame and actual draw.
- `test_miner.py`: nine tests for extraction, filtering, sampling, and preservation of decisions.
- `SHA256SUMS.txt`: checksums of the supplied files.

Existing review CSVs are preserved during analysis. Sampling updates only the selection flag. Changed inputs or sampling settings require a separate output directory.

## Preliminary Analysis

Filtering the snapshot to October 2 leaves **367 issues, 350 comments, 176 keyword candidates, and 174 candidates without extraction discrepancies**. Three issues retain comment-count discrepancies: Braket #1256 and #1322, and IBM Runtime #2777; two are keyword candidates and are excluded from the sampling frame.

The conservative preliminary review of the ten selected cases includes **PennyLane-Qiskit #685** and excludes nine cases. The included issue explicitly associates changes in the IBM transpiler with blocked execution of PennyLane circuits on IBM hardware.

Qiskit Machine Learning #1042 reports a QPY error during an IBM Runtime workflow, but the retained evidence does not clearly identify an infrastructure condition associated with the failure. IBM Runtime #3397 concerns a planned API change for mock devices. Mitiq #3082 discusses a conditional risk whose applicability is challenged and whose proposal is withdrawn. These cases are excluded under the same conservative rule, with their reasons retained in the CSV.

The seven cards describe the integration incompatibility, blocked execution, a reported partial workaround, and information such as the problem report, proposed solution, code, and assessment of a proposal. The discussion does not establish a general solution or a confirmed root cause for every case.
