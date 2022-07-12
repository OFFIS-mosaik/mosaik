"""
Executes all files in bchemanrks subfolder and
compares the execution graph to the contents of the *.gexf file.
"""
import glob
import os
import subprocess
import sys

import pytest

CODE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'benchmarks')
BENCHMARKS = glob.glob(os.path.join(CODE_DIR, 'benchmark*.py'))

@pytest.mark.parametrize('benchmark_filename', BENCHMARKS)
def test_benchmarks(benchmark_filename):
	returncode = subprocess.call([sys.executable, benchmark_filename, '--compare', '1'], cwd=CODE_DIR)
	if returncode == 3:
		print(f'Execution graph of {benchmark_filename} is different than the comparison graph')
	assert returncode == 0
