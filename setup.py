from setuptools import setup, find_packages
import os

find_version='3.2.0'
if os.environ.get('CI_COMMIT_TAG'):
    find_version = os.environ['CI_COMMIT_TAG']



setup(
    name='mosaik',
    version=find_version,
    author='mosaik development team',
    author_email='mosaik@offis.de',
    description='Mosaik is a flexible Smart-Grid co-simulation framework.',
    long_description=(open('README.rst', encoding='utf-8').read() + '\n\n' +
                      open('CHANGES.txt', encoding='utf-8').read() + '\n\n' +
                      open('AUTHORS.txt', encoding='utf-8').read()),
    long_description_content_type='text/x-rst',
    url='https://mosaik.offis.de',
    install_requires=[
        'networkx>=2.5',
        'mosaik-api-v3>=3.0.7',
        'loguru>=0.6.0',
        'tqdm>=4.64.1',
        'typing-extensions>=4.5.0',
    ],
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    entry_points={
        'console_scripts': [
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',    
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
