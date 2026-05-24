from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.nlu", description="RoadSoS NLU utility commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("export-onnx", help="Export best_model.pt to FP32 ONNX")
    subparsers.add_parser("quantize-onnx", help="Quantize FP32 ONNX to INT8")

    benchmark_parser = subparsers.add_parser("benchmark", help="Run the latency benchmark")
    benchmark_parser.add_argument("--count", type=int, default=200, help="Number of sequential predictions to run")

    args = parser.parse_args()

    if args.command == "export-onnx":
        from app.nlu.export_onnx import main as export_main

        export_main()
        return

    if args.command == "quantize-onnx":
        from app.nlu.quantize_onnx import main as quantize_main

        quantize_main()
        return

    if args.command == "benchmark":
        from app.nlu.latency_benchmark import run_latency_benchmark

        report = run_latency_benchmark(sample_count=args.count)
        print(report)
        return


if __name__ == "__main__":
    main()
