from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import numpy as np

from app.nlu.inference_engine import CHECKPOINT_DIR, get_nlu_engine


def _percentile(values: list[float], pct: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float32), pct))


def run_latency_benchmark(sample_count: int = 200) -> dict:
    test_path = Path(__file__).resolve().parent / "dataset" / "test.json"
    results_path = Path(__file__).resolve().parent / "results" / "latency_report.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with open(test_path, encoding="utf8") as fh:
        examples = json.load(fh)

    rng = random.Random(42)
    rng.shuffle(examples)
    texts = [example["text"] for example in examples]
    sample_texts = (texts * ((sample_count + len(texts) - 1) // len(texts)))[:sample_count]

    engine = get_nlu_engine()
    engine.warm_up()

    total_latencies: list[float] = []
    tokenization_latencies: list[float] = []
    inference_latencies: list[float] = []
    crf_latencies: list[float] = []
    post_latencies: list[float] = []
    mode_probe = engine.predict("test")

    for text in sample_texts:
        result = engine.predict(text)
        total_latencies.append(result.latency_ms)
        tokenization_latencies.append(result.timings_ms.get("tokenization_ms", 0.0))
        inference_latencies.append(result.timings_ms.get("inference_ms", 0.0))
        crf_latencies.append(result.timings_ms.get("crf_decoding_ms", 0.0))
        post_latencies.append(result.timings_ms.get("post_processing_ms", 0.0))

    report = {
        "count": len(total_latencies),
        "latency_ms": {
            "p50": _percentile(total_latencies, 50),
            "p90": _percentile(total_latencies, 90),
            "p95": _percentile(total_latencies, 95),
            "p99": _percentile(total_latencies, 99),
            "mean": float(statistics.fmean(total_latencies)),
            "std": float(statistics.pstdev(total_latencies)),
            "min": float(min(total_latencies)),
            "max": float(max(total_latencies)),
        },
        "breakdown_ms": {
            "tokenization_mean": float(statistics.fmean(tokenization_latencies)),
            "inference_mean": float(statistics.fmean(inference_latencies)),
            "crf_decoding_mean": float(statistics.fmean(crf_latencies)),
            "post_processing_mean": float(statistics.fmean(post_latencies)),
        },
        "backend": getattr(mode_probe, "backend", "unknown"),
        "runtime_mode": getattr(mode_probe, "runtime_mode", "unknown"),
    }

    with open(results_path, "w", encoding="utf8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, indent=2))

    suggestions = []
    if report["latency_ms"]["p50"] > 150:
        suggestions.append("Confirm the INT8 model is being loaded instead of the fallback path.")
        suggestions.append("Keep session_options.intra_op_num_threads at 1 for the benchmark.")
        suggestions.append("Reduce max_length if the model is still spending too long in tokenization or inference.")
    if report["latency_ms"]["p99"] > 300:
        suggestions.append("Check for warm-up misses and repeated model initialization across requests.")
        suggestions.append("Verify the ONNX export contains only the encoder and heads, not training-only ops.")

    if report["latency_ms"]["p50"] > 150 or report["latency_ms"]["p99"] > 300:
        raise AssertionError("Latency thresholds not met. Suggestions: " + " | ".join(suggestions))

    return report


def main():
    report = run_latency_benchmark(sample_count=200)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
