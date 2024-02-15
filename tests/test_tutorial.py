"""
Executes all files in /docs/tutorial/code for which an *.out file exists and
compares the output of the script to the contents of the *.out file.
"""
import glob
import os
import subprocess
import sys

import pytest

CODE_DIR = os.path.join(os.path.abspath('.'), 'docs', 'tutorials', 'code')

CASES = glob.glob(os.path.join(glob.escape(CODE_DIR), '*.out'))


@pytest.mark.cmd_process
@pytest.mark.parametrize('outfile', CASES)
def test_tutorial(outfile: str):
    python_file = outfile.rsplit('.', 1)[0] + '.py'
    expected = open(outfile).read()
    out = subprocess.check_output([sys.executable, python_file], cwd=CODE_DIR,
                                  universal_newlines=True)
    assert out == expected
