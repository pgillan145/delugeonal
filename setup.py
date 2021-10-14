#!/usr/bin/env python3

import delugeonal
from setuptools import find_packages, setup

with open('./README.md', encoding='utf-8') as f:
    readme = f.read()

setup(
    author='Patrick Gillan',
    author_email = 'pgillan@minorimpact.com',
    description="Automate and control multiple aspects of a torrent/media infrastructure.",
    entry_points = { "console_scripts": [ "delugeonal = delugeonal:main" ] },
    install_requires=['fuzzywuzzy', 'minorimpact', 'parse-torrent-title', 'torrentool', 'uravo'],
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
