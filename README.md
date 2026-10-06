<div align="center">
  <h1><em>HQC Issues</em></h1>

  <p>
    <strong>
      Code and data for studying quantum infrastructure constraints reported in GitHub issues
    </strong>
  </p>

  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 or later"></a>
    <a href="https://docs.github.com/en/rest"><img src="https://img.shields.io/badge/GitHub-REST%20API-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub REST API"></a>
    <a href="https://docs.python.org/3/library/"><img src="https://img.shields.io/badge/Dependencies-Standard%20Library-3776AB?style=for-the-badge" alt="Python standard library only"></a>
    <a href="#study-scope"><img src="https://img.shields.io/badge/Snapshot-2026--10--06-555555?style=for-the-badge" alt="Snapshot dated October 6, 2026"></a>
  </p>

  <p>
    <a href="#overview">Overview</a> ·
    <a href="#study-scope">Study Scope</a> ·
    <a href="#procedure">Procedure</a> ·
    <a href="#sampling">Sampling</a> ·
    <a href="#getting-started">Getting Started</a> ·
    <a href="#files">Files</a> ·
    <a href="#preliminary-analysis">Preliminary Analysis</a> ·
    <a href="#limitations">Limitations</a>
  </p>
</div>

**Version 0.1.0**

## Overview

This repository contains the code, data, and preliminary analysis for *How Quantum Infrastructure Constrains Hybrid Software: An Empirical Study*.

This pilot tests the collection and classification procedure using ten candidates from five manually selected repositories. The preliminary review includes one issue and excludes nine under a conservative relevance criterion. These results do not establish a complete taxonomy or estimate how common infrastructure problems are.

The preliminary coding was prepared with AI assistance. The CSV files include the reasons and supporting fragments. 

## Study Scope

The selected repositories are:

- `Qiskit/qiskit-ibm-runtime`
- `PennyLaneAI/pennylane-qiskit`
- `qiskit-community/qiskit-machine-learning`
- `amazon-braket/amazon-braket-sdk-python`
- `unitaryfoundation/mitiq`

The analysis period runs from **January 1, 2026, 00:00:00 UTC to October 2, 2026, 23:59:59 UTC**, inclusive. Each issue is analyzed with its title, body, and accessible comments created by the cutoff.

Repository activity and technology evidence are stored in `data/repository_activity_evidence.json` and `data/repository_technology_evidence.json`.

## Procedure

1. Retrieve all issue and comment pages through the GitHub REST API.
2. Exclude pull requests, remove duplicates, and apply the creation-date cutoff.
3. Check comment counts, recheck discrepancies, and flag unresolved cases.
4. Find candidates by matching the keywords in `config.json` against titles, bodies, and retained comments.
5. Randomly select two candidates without extraction discrepancies per repository.
6. Review relevance, record labels and evidence, and group relevant fragments using an adaptation of card sorting.

A match requires at least one keyword. Matching ignores case, respects word boundaries, and treats spaces, hyphens, and underscores as equivalent. No stemming is used. The 54 keywords come from the study concepts and terms discussed during preparation; the vocabulary has not been validated.

The script rejects incomplete searches and searches exceeding GitHub's 1,000-result limit. Comment creation dates are checked separately because the API's `since` parameter uses update dates.

## Sampling

The sample contains **ten issues, two per repository**. This allocation allows the pilot to cover all five sources within the available time. It is not proportional to repository size and does not establish statistical representativeness, a confidence level, or category saturation.

The fixed seed **`20261006`** comes from the package preparation date. Its value is arbitrary and has no statistical meaning. It was set before the recorded draw and kept after reading the cases. Alternative seeds were not tested to obtain more relevant cases.

The code uses `random.Random(seed).sample()`, with repositories sorted by name and candidates by issue number. Reproduction requires the same data, ordering, algorithm, and call sequence. The recorded draw used Python **3.12.14**. The seed, Python version, sampling frame, checksum, and selected IDs are stored in `results/sample_manifest.json`.

Irrelevant cases are kept in the sample and are not replaced. Unselected candidates remain unclassified. Ambiguous cases are excluded when the evidence does not clearly meet the relevance criterion.

## Getting Started

Use Python **3.10 or later**. No third-party packages are required.

From the repository root, reproduce the supplied analysis and preliminary coding without querying GitHub:

```bash
python3 miner.py analyze --output reproduced_results
python3 miner.py sample --output reproduced_results
```

The script generates data columns and selection flags. Qualitative labels come from recorded annotations, rather than keyword matches. It loads `data/review_annotations.json` only when the cutoff, seed, and candidate checksum match. Otherwise, classification fields remain blank and the card file contains only column headers.

To collect new API responses, use separate directories:

```bash
python3 miner.py collect --data new_extraction
python3 miner.py analyze --data new_extraction --output new_results
python3 miner.py sample --output new_results
```

To replay the original October 6 responses offline, copy `data/cache/` and `data/cache_index.json` to a separate directory, then run `python3 miner.py collect --offline --config data/config_used.json --data <copied-directory>`. Exit code 1 is expected because three comment-count discrepancies remain in that snapshot.

## Files

The script generates **two CSV files**:

- `results/manual_review.csv`: all 176 candidates, their text, metadata, keyword matches, extraction checks, sample selection, and review fields. Reviewed rows include relevance decisions, RQ labels, and evidence. Filter `selected_for_sample` to `True` to see the ten sampled cases. Unselected rows have blank classification fields.
- `results/cards_proposed.csv`: seven preliminary cards from the included issue. Each card contains one idea, its source, RQ, and group. The groups remain preliminary.

Other files document the inputs and procedure:

- `config.json`: repositories, period, keywords, and sampling settings.
- `miner.py`: command-line entry point.
- `hqc_issues/`: modules for storage, API access, collection, analysis, sampling, and command-line execution.
- `data/`: source issues, cached responses, collection checks, repository evidence, and preliminary annotations.
- `results/summary.json`: collection counts and preliminary coding summary.
- `results/sample_manifest.json`: sampling frame and recorded selection.
- `test_miner.py`: nine tests covering extraction, filtering, sampling, and preservation of decisions.
- `SHA256SUMS.txt`: file checksums.

Analysis preserves existing review CSVs. Sampling only updates the selection flag. Use a separate output directory when changing inputs or sampling settings.

## Preliminary Analysis

Filtering the snapshot to October 2 leaves **367 issues, 350 comments, 176 keyword candidates, and 174 candidates without extraction discrepancies**. Three issues have unresolved comment-count discrepancies: Braket #1256 and #1322, and IBM Runtime #2777. Two are keyword candidates and are excluded from sampling.

The preliminary review includes **PennyLane-Qiskit #685** and excludes the other nine sampled cases. The included issue reports that changes in the IBM transpiler block the execution of PennyLane circuits on IBM hardware.

Qiskit Machine Learning #1042 reports a QPY error in an IBM Runtime workflow, but its retained text does not clearly identify a related infrastructure condition. IBM Runtime #3397 concerns a planned API change for mock devices. Mitiq #3082 discusses a possible risk whose applicability is questioned and whose proposal is withdrawn. Their exclusion reasons are recorded in the CSV.

The seven cards cover integration incompatibility, blocked execution, a reported partial workaround, and information such as the problem report, proposed solution, code, and assessment of a proposal. The discussion does not establish a general solution or independently verify the reported cause.
