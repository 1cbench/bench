import argparse
from pathlib import Path
from bench.benchmark_runner import BenchmarkRunner


def derive_output_path(source: str) -> str:
    p = Path(source)
    stem = p.stem
    new_stem = "runreport_" + (stem[len("output_"):] if stem.startswith("output_") else stem)
    return str(p.with_name(new_stem + ".json"))


def main():
    parser = argparse.ArgumentParser(description="Run 1C benchmark on a source file")
    parser.add_argument("source", help="Path to the source CSV file with tasks")
    parser.add_argument(
        "--output", "-o",
        help="Path to JSON file for storing statistics (auto-derived from source if omitted)",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual execution)"
    )
    args = parser.parse_args()

    output_path = args.output or derive_output_path(args.source)

    bench = BenchmarkRunner()
    stats = bench.run(
        filename=args.source,
        dry_run=args.dry_run,
        output_path=output_path,
    )

    # Print results to console
    print(f"\nFinal Statistics:")
    print(f"Total samples: {stats['number_of_samples']}")
    print(f"Compile rate: {stats['compile_rate']:.2%}")
    print(f"Success rate: {stats['success_rate']:.2%}")

    if stats.get('compile_failed_ids'):
        print(f"\nCompile failed ({len(stats['compile_failed_ids'])} cases):")
        for task_id in stats['compile_failed_ids']:
            print(f"  - {task_id}")

    if stats.get('success_failed_ids'):
        print(f"\nSuccess failed ({len(stats['success_failed_ids'])} cases):")
        for task_id in stats['success_failed_ids']:
            print(f"  - {task_id}")

    print(f"\nStatistics saved to: {output_path}")


if __name__ == "__main__":
    main()
