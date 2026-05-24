# RoadSoS - Research Paper & Standards Alignment
**PS #9 - Multilingual Emergency Intent Parsing & Triage**

This document maps the current RoadSoS implementation to the research and standards themes in the PS specification.

## Paper 1: Chen et al. (2019) - Joint Intent Classification and Slot Filling

| Paper Mechanism | RoadSoS Implementation | File |
|---|---|---|
| Shared encoder for intent and slots | `EmergencyNLUModel` uses one multilingual encoder for both heads | [backend/app/nlu/model.py](backend/app/nlu/model.py) |
| Intent head on pooled representation | CLS token feeds the intent linear layer | [backend/app/nlu/model.py](backend/app/nlu/model.py) |
| Slot tagging from contextual token states | Per-token slot head predicts slot labels over the same encoder output | [backend/app/nlu/model.py](backend/app/nlu/model.py) |
| Joint decision making | `run_nlu_pipeline()` returns intent, slots, triage, and follow-up in one pass | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |

Key alignment: RoadSoS keeps intent and slot extraction coupled at the representation level, then converts the joint output into triage decisions. The current repository uses a CRF-based supervised model rather than the paper's exact decoder shape, but the architectural intent is the same.

## Paper 2: MASSIVE / Multilingual NLU Benchmarks

| Paper Mechanism | RoadSoS Implementation | File |
|---|---|---|
| Cross-lingual generalisation | Dataset includes English, Bengali, Hindi, Thai, Sinhala, and mixed-script examples | [backend/app/nlu/dataset/panic_data.json](backend/app/nlu/dataset/panic_data.json) |
| BIO sequence labeling | The expanded corpus ships BIO tags for slot spans | [backend/app/nlu/dataset/panic_data_bio.json](backend/app/nlu/dataset/panic_data_bio.json) |
| Minimal task-specific supervision | The runtime can boot in fallback mode when checkpoints are unavailable | [backend/app/nlu/inference_engine.py](backend/app/nlu/inference_engine.py) |
| Non-Latin scripts and code switching | Adversarial Phase A/B/C fixtures include Bengali, Thai, Hindi, Sinhala, and mixed-script messages | [tests/adversarial/](tests/adversarial/) |

Key alignment: the benchmark corpus is deliberately multilingual and stress-tests script diversity, which matches the core motivation of MASSIVE-style evaluation even though the emergency domain is different.

## Paper 3: Joint Intent + Slot Filling Surveys

| Survey Finding | RoadSoS Decision | Rationale |
|---|---|---|
| Slot-intent coupling improves frame-level accuracy | Triage is derived from both intent and extracted slot evidence | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |
| Boundary-aware slot extraction matters | The slot layer is validated against BIO spans and normalized slot keys | [backend/app/dialogue/state_machine.py](backend/app/dialogue/state_machine.py) |
| Robustness matters under noisy text | The adversarial harness injects noise and evaluates crash-free recovery | [tests/adversarial/noise_injector.py](tests/adversarial/noise_injector.py) |
| Missing information should trigger a follow-up | The response path emits a follow-up question when required slots are absent | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |

Key alignment: RoadSoS treats intent, slots, and triage as a single user-facing frame, then falls back to clarification when the frame is incomplete.

## CAP v1.2 Emergency Messaging Standard

| CAP Field | RoadSoS Mapping | File |
|---|---|---|
| `identifier` | UUID-based alert identifier | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `sender` | Stable sender string `roadsos-nlu-v1` | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `sent` | UTC ISO-8601 timestamp | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `status` | `Actual` | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `msgType` | `Alert` | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `scope` | `Restricted` | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.category` | `Transport` | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.event` | Intent-to-event mapping | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.urgency` | P1/P2/P3 mapped to Immediate/Expected/Future | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.severity` | P1/P2/P3 mapped to Extreme/Severe/Moderate | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.description` | Raw message text | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| `info.area.areaDesc` | Location slot if present | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |

Key alignment: the CAP exporter is deterministic and validates the mandatory envelope fields before returning the alert payload.

## Priority Dispatch Logic

| Dispatch Rule | RoadSoS Behaviour | File |
|---|---|---|
| Entrapment escalates to critical | Entrapment contributes to P1 selection | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |
| Fire or fuel leak escalates to critical | Hazard type `fire` or `fuel_leak` feeds P1 handling | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |
| Multiple casualties increase urgency | Casualty count changes the triage decision | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |
| Vehicle assistance should not over-escalate | Assistance is handled through the same frame logic, with conservative defaults | [backend/app/nlu/pipeline.py](backend/app/nlu/pipeline.py) |

## Operational Benchmarking and Release Flow

| Capability | RoadSoS Implementation | File |
|---|---|---|
| Latency benchmarking | Reusable benchmark runner with percentile reporting | [backend/app/nlu/latency_benchmark.py](backend/app/nlu/latency_benchmark.py) |
| CLI entrypoint | `python -m app.nlu benchmark`, `export-onnx`, `quantize-onnx` | [backend/app/nlu/__main__.py](backend/app/nlu/__main__.py) |
| ONNX export | Export script for the trained checkpoint | [backend/app/nlu/export_onnx.py](backend/app/nlu/export_onnx.py) |
| INT8 quantization | Dynamic quantization helper for ONNX | [backend/app/nlu/quantize_onnx.py](backend/app/nlu/quantize_onnx.py) |
| API latency reporting | `GET /api/triage/latency` and response header timing | [backend/app/routers/triage.py](backend/app/routers/triage.py) |
| Startup warmup | Engine warm-up at application startup | [backend/app/main.py](backend/app/main.py) |

## PS Deliverable Compliance Matrix

| Tier | Deliverable | Status | Evidence |
|---|---|---|---|
| Tier 1 | FastAPI triage endpoint | Complete | [backend/app/main.py](backend/app/main.py), [backend/app/routers/triage.py](backend/app/routers/triage.py) |
| Tier 1 | CAP v1.2 output | Complete | [backend/app/nlu/cap_exporter.py](backend/app/nlu/cap_exporter.py) |
| Tier 1 | Multilingual panic dataset | Complete | [backend/app/nlu/dataset/](backend/app/nlu/dataset/) |
| Tier 2 | Multilingual robustness harness | Complete | [tests/adversarial/run_adversarial.py](tests/adversarial/run_adversarial.py) |
| Tier 2 | Noise injection | Complete | [tests/adversarial/noise_injector.py](tests/adversarial/noise_injector.py) |
| Tier 2 | Latency instrumentation | Complete | [backend/app/nlu/latency_benchmark.py](backend/app/nlu/latency_benchmark.py) |
| Tier 2 | ONNX export / quantization code | Complete | [backend/app/nlu/export_onnx.py](backend/app/nlu/export_onnx.py), [backend/app/nlu/quantize_onnx.py](backend/app/nlu/quantize_onnx.py) |
| Tier 3 | Submission-grade exported ONNX artifacts | Not present in this checkout | Artifacts referenced by the prompt are not stored in the workspace |

## Notes on Current Checkout

The repository matches the intended system shape described in the prompt, but the actual exported ONNX weights are not present in this workspace. That means the alignment document can confirm the design and implementation mapping, but not claim a submission-grade INT8 runtime artifact from the current checkout.
