#!/usr/bin/env python3

import minorimpact
import configparser
import delugeonal
import os
import tempfile
import unittest
from unittest import mock
import random
import subprocess
import sys
import time

class TestUtils(unittest.TestCase):
    test_dir = None

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        os.chdir(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_001_config(self):
        config = minorimpact.config.getConfig(script_name='delugeonal')
        self.assertIsNotNone(config)
        self.assertIsInstance(config, configparser.ConfigParser)

    def test_002_rss(self):
        delugeonal.delugeonal.load_libraries()
        for site in (delugeonal.delugeonal.mediasites):
            feed = site.rss_feed()
            self.assertTrue(len(feed) > 0)

if __name__ == '__main__':
    unittest.main()
