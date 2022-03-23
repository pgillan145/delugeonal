#!/usr/bin/env python3

import delugeonal
from setuptools import find_packages, setup

with open('./README.md', encoding='utf-8') as f:
    readme = f.read()

setup(
    author='Patrick Gillan',
    author_email = 'pgillan@minorimpact.com',
    classifiers = [
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        ],
    description="Automate and control multiple aspects of a torrent/media infrastructure.",
    entry_points = { "console_scripts": [ "delugeonal = delugeonal:main" ] },
    install_requires=['dumper', 'fuzzywuzzy', 'IMDbPy', 'minorimpact', 'parse-torrent-title', 'plexapi', 'pyyaml', 'tvdb_v4_official', 'uravo', 'bencode.py'],
    license='GPLv3',
    long_description = readme,
    long_description_content_type = 'text/markdown',
    name='delugeonal',
    packages=find_packages(),
    setup_requires=[],
    tests_require=[],
    url = "https://github.com/pgillan145/delugeonal",
    version=delugeonal.__version__,
)
