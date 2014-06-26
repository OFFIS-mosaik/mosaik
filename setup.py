from setuptools import setup, find_packages


setup(
    name='mosaik',
    version='2.0a3',
    author='Stefan Scherfke',
    author_email='stefan.scherfke at offis.de',
    description=('Mosaik is a flexible Smart-Grid co-simulation framework.'),
    long_description=(open('README.txt').read() + '\n\n' +
                      open('CHANGES.txt').read() + '\n\n' +
                      open('AUTHORS.txt').read()),
    url='https://moaik.offis.de',
    install_requires=[
        'networkx>=1.8.1',
        'mosaik-api>=2.0a3',
        'simpy>=3.0.5',
        'simpy.io>=0.2',
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
