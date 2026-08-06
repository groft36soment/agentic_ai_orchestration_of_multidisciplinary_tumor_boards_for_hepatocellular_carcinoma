# HERA multidisciplinary tumor-board orchestration

HERA separates hepatocellular carcinoma treatment assessment into a Tumor Staging Axis and a Hepatic Reserve Axis. Radiology and medical oncology agents assess tumor burden, while hepatology and transplant surgery agents assess functional reserve. Pathology and interventional radiology bridge the two axes. Divergent recommendations enter a typed Epistemic Arbitration Protocol with PROPOSE, CHALLENGE, BRIDGE, and SYNTHESIZE acts. The output is a CUSE-aligned decision packet containing decomposed confidence, evidence, minority findings, and reopen conditions.

This software is intended for retrospective research evaluation. It does not provide medical advice and must not be used as an autonomous clinical decision system.

## Installation

Python 3.11 is required.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

The pinned conda environment is available through:

```bash
conda env create -f environment.yml
conda activate hera-mdt
```

The container image can be built with:

```bash
docker build -t hera-mdt:1.0.0 .
```

## Data

The canonical dataset addresses are collected in `dataset_links.txt`.

TCGA-LIHC uses GDC Data Release 39.0. Open clinical metadata can be requested from the GDC project page. Controlled files require dbGaP authorization. The analysis cohort contains 362 eligible cases from 377 project participants after applying confirmed HCC histology, sufficient staging variables, documented first-course treatment, and the exclusion rules below.

SEER uses the November 2023 Research Plus submission and diagnosis years 2004–2020. Access requires an approved account and acceptance of the applicable NCI agreement. The local import contains no download automation because individual-level SEER records cannot be redistributed. Users must verify that their approved research purpose, location, infrastructure, software, and data handling satisfy the current SEER policy before processing any record. The analysis cohort contains 83,471 eligible HCC cases.

Required inclusion criteria are confirmed HCC histology, sufficient variables to determine BCLC stage, and documented first-course treatment. Exclusions are missing staging, missing treatment, second primary malignancy, and autopsy-only diagnosis. SEER HCC selection uses ICD-O-3 topography C22.0 and morphology 8170–8175.

Input is CSV or JSON Lines. Required columns are `patient_id` and `age`. Supported clinical fields are `sex`, `tumor_size_cm`, `tumor_count`, `vascular_invasion`, `extrahepatic_spread`, `performance_status`, `child_pugh_score`, `meld_score`, `albumin_g_dl`, `bilirubin_mg_dl`, `inr`, `platelets_10e9_l`, `ascites`, `encephalopathy`, `portal_hypertension`, `afp_ng_ml`, `fibrosis_stage`, `etiology`, `first_course_treatment`, and `registry`.

Validate an authorized local export and create its manifest:

```bash
hera-prepare data/authorized/hcc_registry.csv --output outputs/data_manifest.json
```

The manifest records the exact input SHA-256, record count, and registry counts. Expected disk use depends on the approved export fields. A clinical-only CSV is typically below 250 MB; genomic and imaging assets are outside the evaluation input and can be substantially larger.

## Knowledge preparation

The `knowledge` directory contains small decision-node fixtures for software checks. Formal evaluation requires locally licensed, version-matched text from BCLC 2026, NCCN HCC Version 1.2026, and AASLD 2023. Name each chunk as `source__version__axis__decision_node.txt`. Axis values are `tumor_staging`, `hepatic_reserve`, and `bridge`. Do not commit licensed guideline text unless redistribution is permitted.

## Running HERA

Generate decision packets:

```bash
hera-run data/authorized/hcc_registry.csv --knowledge knowledge --output outputs/decisions.jsonl
```

Each packet includes the treatment category, BCLC stage, TSA/HRA/integrated confidence, evidence records, up to three deliberation rounds, a minority report when convergence is not reached, CUSE dimensions, reopen conditions, and elapsed processing time.

The five treatment categories are curative resection or ablation, transplantation, locoregional treatment, systemic treatment, and best supportive care. EAP activates only when TSA and HRA treatment categories differ. The viable option set must narrow or remain unchanged each round. Nonconvergence after three rounds preserves the dissenting axis.

## Evaluation

Run the complete registry evaluation:

```bash
hera-evaluate data/authorized/hcc_registry.csv --knowledge knowledge --output outputs/evaluation.json
```

The primary metric is exact treatment-category concordance. Secondary metrics include Cohen's kappa, percentile bootstrap confidence intervals with 1,000 resamples, expected calibration error, BCLC-stage results, registry results, median processing time, and EAP activation rate. Paired baseline comparisons use exact McNemar tests and Bonferroni adjustment over seven comparisons.

The paper reports the following reference values:

| Analysis | Expected value | Acceptance tolerance |
|---|---:|---:|
| TCGA-LIHC concordance | 78.4% | 0.5 percentage points |
| SEER concordance | 74.8% | 0.5 percentage points |
| Pooled concordance | 76.2% | 0.3 percentage points |
| Pooled Cohen's kappa | 0.61 | 0.03 |
| BCLC-0/A concordance | 85.3% | 0.5 percentage points |
| BCLC-B concordance | 68.7% | 0.5 percentage points |
| BCLC-C concordance | 54.6% | 0.5 percentage points |
| BCLC-D concordance | 88.9% | 0.5 percentage points |
| EAP activation | 30.4% | 1.0 percentage point |
| Confidence ECE | 0.042 | 0.01 |

The `configs/ablation.yaml` file enumerates every main component and individual-agent ablation. `configs/supplementary.yaml` enumerates cross-registry, subgroup, prompt, backbone, retrieval-depth, temperature, staging-noise, edge-case, guideline-version, run-stability, failure, CUSE, EAP, disagreement, distribution, transfer, scaling, and agent-combination analyses.

## Compute budget

The framework does not train neural network parameters. Batch size, gradient accumulation, learning rate, epochs, scheduler, precision, GPU count, VRAM, and training storage are therefore not applicable. The paper reports GPT-4o as the default backbone, temperature 0.3 for the five-run stability analysis, six agents, and up to three EAP rounds.

The reported median end-to-end time is 4.2 minutes per case with an interquartile range of 2.8–6.1 minutes and throughput near 11 cases per hour. EAP-activated cases require a median 5.7 minutes; axis-concordant cases require 2.6 minutes. Exact infrastructure, GPU type, VRAM, storage, and total wall time were not reported. Runtime depends on model-service latency, retrieval storage, concurrency limits, and the fraction of cases entering arbitration. A full 83,833-case serial run at the reported median would require about 5,868 hours, so formal evaluation requires approved parallel execution and careful rate-limit planning.

No patient record is sent to an external model service by this package. The included specialists are deterministic, inspectable decision components used to test orchestration and evaluation. Any connection to a hosted model must be implemented by the deploying institution under its privacy, security, clinical governance, and dataset agreement obligations.

## Quality checks

Run the test suite and static checks:

```bash
pytest -q
ruff check .
mypy --strict src/hera_mdt
```

The tests cover clinical scoring, BCLC mapping, knowledge-axis isolation, six-agent structure, evidence production, monotonic EAP convergence, decision packets, data validation, exact treatment metrics, bootstrap intervals, McNemar testing, calibration, Bonferroni adjustment, and the complete 384-cell decision matrix.

## Safety boundaries

Registry rows must remain de-identified. Do not place credentials, access tokens, patient identifiers, free-text clinical notes, or raw controlled records in source control. Preserve the authorized data release, selection query, input manifest, software environment, guideline versions, model endpoint version, sampling settings, and execution logs for each study run. Clinician review is required for every output, with priority review for BCLC-C, missing direct liver-function measurements, EAP nonconvergence, low confidence, and reopen-condition triggers.
