from setuptools import setup, find_packages

import mosaik


setup(
    name='mosaik',
    version=mosaik.__version__,
    author='Stefan Scherfke',
    author_email='stefan.scherfke at offis.de',
    description=('Mosaik is a simulation compositor and comes with a powerful '
                 'scenario specification framework.'),
    long_description=(open('README.txt').read() + '\n\n' +
                      open('CHANGES.txt').read() + '\n\n' +
                      open('AUTHORS.txt').read()),
    url='https://moaik.offis.de',
    license='Proprietary',
    install_requires=[
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
        ],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Scientific/Engineering',
    ],
)
