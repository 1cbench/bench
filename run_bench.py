import argparse
import json
from bench.benchmark_runner import BenchmarkRunner


def main():
    parser = argparse.ArgumentParser(description="Run 1C benchmark on a source file")
    parser.add_argument("source", help="Path to the source CSV file with tasks")
    parser.add_argument(
        "--output", "-o",
        help="Path to JSON file for storing statistics",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual execution)"
    )
    args = parser.parse_args()

    bench = BenchmarkRunner()
    stats = bench.run(
        filename=args.source,
        dry_run=args.dry_run,
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

    # Save stats to JSON file if specified
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"\nStatistics saved to: {args.output}")


if __name__ == "__main__":
    main()
