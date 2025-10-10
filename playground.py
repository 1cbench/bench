from bench.benchmark_runner import BenchmarkRunner
from bench.constants import DATABASE_PATH, USER_NAME
from bench.one_c_runner import OneCEngine


def main0():
    engine = OneCEngine(DATABASE_PATH, USER_NAME)
    engine.update_processing()
    # engine.run_processing()


def main():
    filename = "data/stage_tasks2.csv"
    bench = BenchmarkRunner()
    bench.run(
        filename=filename,
        dry_run=True,
    )


if __name__ == "__main__":
    main()