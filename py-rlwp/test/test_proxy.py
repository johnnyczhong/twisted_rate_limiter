# test twisted proxy server

import sys
import PsuedoProxy as p
from twisted.trial import unittest


class ProxyTestCase(unittest.TestCase):
    def setUp(self):
        p.main()
