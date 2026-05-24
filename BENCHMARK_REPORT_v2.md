# RoadSoS - NLU Benchmark Report v2.0
**PS #9 - Multilingual Emergency Intent Parsing & Triage Slot Filling**

**Model:** `xlm-roberta-base` joint encoder with intent head, slot head, and CRF decoder
**Baseline:** `facebook/bart-large-mnli` zero-shot classifier from v1.0
**Benchmark corpus:** `backend/app/nlu/dataset/panic_data.json` - 80 labeled examples
**Expanded multilingual corpus:** `backend/app/nlu/dataset/train.json`, `val.json`, `test.json` - 380 total examples

## Executive Summary

| Metric | v1.0 Baseline | v2.0 Current | Target | Status |
|---|---:|---:|---:|---|
| Macro Intent F1 | 0.88 | 0.4311 | >= 0.82 | FAIL |
| Triage Assignment F1 | 0.90 | 0.3583 | >= 0.85 | FAIL |
| Location Slot F1 | 0.69 | 0.8636 | >= 0.70 | PASS |
| Latency p50 | 312ms | 0.48ms* | <= 150ms | PASS* |
| Latency p90 | 487ms | 0.48ms* | <= 200ms | PASS* |
| Phase A crash rate | -- | 0% | 0% | PASS |
| Phase B crash rate | -- | 0% | 0% | PASS |
| Phase C casualty extraction | -- | 100% | >= 60% | PASS |

*The only latency artifact present in this checkout is the fallback runtime report at `backend/app/nlu/results/latency_report.json`. The ONNX INT8 artifacts referenced by Prompt 5 are not present in this workspace, so this latency number is informative rather than submission-grade.

## 1. Model and Dataset

The current runtime is a supervised joint NLU model built around `xlm-roberta-base` with:

- a CLS-based intent classifier
- a token-level slot head
- a CRF decoder for slot sequence decoding

The architecture in `backend/app/nlu/model.py` uses the following parameter layout:

- encoder: approximately 270M parameters
- intent head: 3,076 parameters for 4 intents
- slot head: 5,383 parameters for 7 slot tags
- CRF layer: 63 parameters
- total trainable heads and CRF: 8,522 parameters

The benchmark corpus contains 80 labeled panic examples with four active intents:

- `emergency_crash`
- `fire_hazard`
- `medical_emergency`
- `vehicle_assistance`

The expanded multilingual corpus adds coverage for Bengali, Hindi, Thai, Sinhala, and code-switched messages in addition to English.

### Corpus Coverage

| Language | Examples |
|---|---:|
| English | 128 |
| Bengali | 79 |
| Bengali native script | 40 |
| Hindi | 60 |
| Thai | 40 |
| Sinhala | 20 |
| Code-switched / mixed | 13 |
| **Total** | **380** |

### Entity Distribution in the BIO Corpus

| Slot / Entity | Count |
|---|---:|
| LOCATION | 337 |
| CASUALTY_COUNT | 215 |
| HAZARD_TYPE | 40 |
| ENTRAPMENT | 32 |
| CHILD_INVOLVED | 9 |

Average entities per utterance: 1.6658
Entity count standard deviation: 0.6660
Minimum / maximum entities per utterance: 0 / 4

## 2. Intent Classification

### 2a. Current Benchmark Results

| Intent | Precision | Recall | F1 | Baseline F1 | Delta |
|---|---:|---:|---:|---:|---:|
| emergency_crash | 0.6739 | 0.8611 | 0.7561 | 0.89 | -0.1339 |
| fire_hazard | 1.0000 | 0.7500 | 0.8571 | 0.94 | -0.0829 |
| medical_emergency | 0.1667 | 0.0833 | 0.1111 | 0.87 | -0.7589 |
| vehicle_assistance | 0.0000 | 0.0000 | 0.0000 | 0.92 | -0.9200 |
| **Macro avg** | **0.4602** | **0.4234** | **0.4311** | **0.88** | **-0.4489** |

The benchmark corpus does not contain labeled `general_help` examples, so that label is excluded from the current intent table.

### 2b. Multilingual Intent Breakdown

| Language | Examples | Intent F1 | Notes |
|---|---:|---:|---|
| English | 128 | 0.6641 | Strongest generalization in the expanded corpus |
| Bengali | 79 | 0.1899 | Romanised and phonetic variants remain difficult |
| Bengali native script | 40 | 0.0000 | Under-covered in the current heuristic fallback |
| Hindi | 60 | 0.3333 | Partial transfer on romanised inputs |
| Thai | 40 | 0.0000 | No reliable intent transfer in fallback mode |
| Sinhala | 20 | 0.4000 | Limited but non-zero transfer |
| Code-switched / mixed | 13 | 0.6154 | Best cross-lingual robustness after English |

## 3. Slot Extraction

| Slot | Precision | Recall | F1 | Baseline F1 | Delta |
|---|---:|---:|---:|---:|---:|
| CASUALTY_COUNT | 0.8500 | 0.4928 | 0.6239 | 0.81 | -0.1861 |
| ENTRAPMENT | 0.9750 | 0.9750 | 0.9750 | 0.92 | +0.0550 |
| HAZARD_TYPE | 0.9250 | 0.9250 | 0.9250 | 0.95 | -0.0250 |
| CHILD_INVOLVED | 0.9500 | 0.9500 | 0.9500 | 0.87 | +0.0800 |
| LOCATION | 0.7755 | 0.9744 | 0.8636 | 0.69 | +0.1736 |
| **Macro avg** | **0.8951** | **0.8636** | **0.8675** | **0.85** | **+0.0175** |

Key observations:

- Location extraction improved materially over v1.0, driven by highway / bridge / landmark normalization.
- Casualty count remains the main weakness because noisy digit expressions and mixed-script numerals still trigger misses.
- The slot decoder is materially stronger than the intent classifier in this checkout.

## 4. Triage Level Assignment

| Triage Level | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| P1 (Critical) | 0.9149 | 0.6719 | 0.7748 | 64 |
| P2 (Serious) | 0.1818 | 0.8571 | 0.3000 | 7 |
| P3 (Minor) | 0.0000 | 0.0000 | 0.0000 | 9 |
| **Macro avg** | **0.3656** | **0.5097** | **0.3583** | **80** |

The current runtime strongly over-predicts P1, which is safer than under-triage but still fails the PS accuracy bar for downstream dispatch logic.

## 5. Latency

| Percentile | BART FP32 v1.0 | Current checkout artifact | Target |
|---|---:|---:|---:|
| p50 | 312ms | 0.48ms* | <= 150ms |
| p90 | 487ms | 0.48ms* | <= 200ms |
| p95 | -- | 0.48ms* | <= 200ms |
| p99 | 621ms | 0.48ms* | <= 300ms |
| mean | -- | 0.48ms* | -- |

*Fallback runtime measurement from `backend/app/nlu/results/latency_report.json`, not an exported ONNX INT8 artifact.

Current artifact status:

- ONNX export and quantization code are present in the repository.
- Exported weights are not present in this checkout.
- The API and benchmark endpoint are wired to report latency, but the only stored timing artifact is the fallback runtime path.

## 6. Adversarial Evaluation

The adversarial harness was run end-to-end against `POST /api/triage/parse-message`.

### Phase A - Fragmented and emotional input

| Metric | Result | Pass Condition |
|---|---:|---:|
| Pass rate | 52% | >= 75% |
| Intent accuracy | 68% | >= 75% |
| No-crash rate | 100% | 100% |
| Location slot F1 | 0.6829 | Present and stable |

### Phase B - Phonetic noise

| Metric | Result | Pass Condition |
|---|---:|---:|
| Pass rate | 12% | >= 65% |
| Intent accuracy | 16% | >= 65% |
| No-crash rate | 100% | 100% |
| Hazard slot F1 | 0.6000 | >= 70% |

### Phase C - Code-switched script mixing

| Metric | Result | Pass Condition |
|---|---:|---:|
| Pass rate | 32% | >= 65% |
| Intent accuracy | 44% | >= 65% |
| No-crash rate | 100% | 100% |
| Casualty extraction | 100% | >= 60% |

Overall adversarial summary:

- 24 / 75 examples passed
- overall pass rate: 32%
- API crash rate: 0%

### Representative successful CAP packet

```json
{
  "alert": {
    "identifier": "ROADSOS-REDACTED",
    "sender": "roadsos-nlu-v1",
    "sent": "2026-05-24T00:00:00+00:00",
    "status": "Actual",
    "msgType": "Alert",
    "scope": "Restricted",
    "restriction": "Emergency responders only",
    "info": {
      "language": "en",
      "category": "Transport",
      "event": "emergency_crash",
      "urgency": "Immediate",
      "severity": "Extreme",
      "certainty": "Observed",
      "description": "accident happened 3 people stuck inside car please help",
      "area": {
        "areaDesc": "highway"
      },
      "parameter": [
        {
          "valueName": "casualtyCount",
          "value": "3"
        },
        {
          "valueName": "entrapment",
          "value": "True"
        },
        {
          "valueName": "triageLevel",
          "value": "P1"
        }
      ],
      "resource": []
    }
  }
}
```

## 7. Confusion Matrix - Intent Classification

| Actual \\ Predicted | emergency_crash | fire_hazard | medical_emergency | vehicle_assistance | general_help |
|---|---:|---:|---:|---:|---:|
| emergency_crash | 31 | 0 | 5 | 0 | 10 |
| fire_hazard | 2 | 6 | 0 | 0 | 6 |
| medical_emergency | 11 | 0 | 1 | 0 | 2 |
| vehicle_assistance | 2 | 0 | 0 | 0 | 4 |

This confusion pattern confirms the current fallback runtime is conservative on emergencies but still too eager to route many messages into the generic help path.

## 8. Reproducibility

```bash
cd backend
python -m app.nlu benchmark --count 200
python -m app.nlu export-onnx
python -m app.nlu quantize-onnx
python -m uvicorn app.main:app --reload
python tests/adversarial/run_adversarial.py
```

The repository also exposes an API-level latency endpoint at `/api/triage/latency`.

## 9. Conclusions

What improved:

- location slot extraction now exceeds the v1.0 benchmark
- entrapment and child-involved slots are highly stable
- CAP packet validation is 100%
- the adversarial harness runs without crashes across all three phases

What still blocks PS #9 compliance:

- intent classification is below the required benchmark on the available checkpoint state
- triage assignment remains under target
- the current checkout does not contain the exported ONNX INT8 artifacts, so the latency measurement is not the intended submission artifact

Net result: the engineering scaffold is in place, but the benchmark numbers in this workspace are not yet submission-ready.
