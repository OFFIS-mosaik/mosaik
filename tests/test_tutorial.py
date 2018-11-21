"""
Executes all files in /docs/tutorial/code for which an *.out file exists and
compares the output of the script to the contents of the *.out file.
"""
import glob
import os
import subprocess
import sys

import pytest


CODE_DIR = os.path.join(os.path.dirname(__file__), '..',
                        'docs', 'tutorial', 'code')
CASES = glob.glob(os.path.join(CODE_DIR, '*.out'))


@pytest.mark.parametrize('outfile', CASES)
def test_tutorial(outfile):
    pyfile = outfile.rsplit('.', 1)[0] + '.py'
    expected = open(outfile).read()
    out = subprocess.check_output([sys.executable, pyfile], cwd=CODE_DIR,
                                  universal_newlines=True)
    assert out == expected
