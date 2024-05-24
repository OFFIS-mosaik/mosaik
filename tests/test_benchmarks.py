"""
Executes all files in bchemanrks subfolder and
compares the execution graph to the contents of the *.gexf file.
"""
import glob
import os
import subprocess
import sys

import pytest


benchmarks = [
    os.path.abspath(file) for file in glob.glob("tests/benchmarks/benchmark*.py")
]


@pytest.mark.benchmark(min_rounds=1, warmup=False)
@pytest.mark.parametrize("benchmark_filename", benchmarks)
def test_benchmarks(benchmark, benchmark_filename):
    returncode = benchmark(run_it, benchmark_filename)
    if returncode == 3:
        print(
            f"Execution graph of {benchmark_filename} is different than the comparison "
            "graph."
        )
    assert returncode == 0


def run_it(benchmark_filename):
    return subprocess.call([sys.executable, benchmark_filename, "--compare", "1"])
