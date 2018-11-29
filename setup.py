from setuptools import setup, find_packages


setup(
    name='mosaik',
    version='2.5.1',
    author='Stefan Scherfke',
    author_email='mosaik@offis.de',
    description=('Mosaik is a flexible Smart-Grid co-simulation framework.'),
    long_description=(open('README.txt', encoding='utf-8').read() + '\n\n' +
                      open('CHANGES.txt', encoding='utf-8').read() + '\n\n' +
                      open('AUTHORS.txt', encoding='utf-8').read()),
    url='https://mosaik.offis.de',
    install_requires=[
        'networkx>=2.0',
        'mosaik-api>=2.2',
        'simpy>=3.0.10',
        'simpy.io>=0.2.3',
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
