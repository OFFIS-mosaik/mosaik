"""
Executes all files in /docs/tutorial/code for which an *.out file exists and
compares the output of the script to the contents of the *.out file.

"""
import glob
import os
import subprocess
import sys

import pytest

# ONLY FOR PYCHARM:
# Becasue of a missing entry in the environmet variable 'PATH' casued by PYCHARM is it necessarily to append
# the missing part. The bug occurs only in PyCharm's run mode
os.environ['PATH']= os.environ['PATH'] + ':/home/onannen/.virtualenvs/mosaik-demo/bin'

CODE_DIR = os.path.join(os.path.dirname(__file__), '..',
                        'docs', 'tutorial', 'code')
CASES = glob.glob(os.path.join(CODE_DIR, '*.out'))


@pytest.mark.parametrize('outfile', CASES)
def test_tutorial(outfile, monkeypatch):
    pyfile = outfile.rsplit('.', 1)[0] + '.py'
    expected = open(outfile).read()
    # monkeypatch.syspath_prepend(CODE_DIR)
    # monkeypatch.chdir(CODE_DIR)
    out = subprocess.check_output([sys.executable, pyfile], cwd=CODE_DIR,
                                  universal_newlines=True)
    assert out == expected
