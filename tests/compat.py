#
# Compatibilty layer with TestCase
#
import unittest

import pytest

case = unittest.TestCase()

class TestCase:
    assertCountEqual = case.assertCountEqual
    assertFalse = case.assertFalse
    assertEqual = case.assertEqual
    assertTrue = case.assertTrue
    assertListEqual = case.assertListEqual
    assertDictEqual = case.assertDictEqual
    assertRaises = case.assertRaises
    assertIsInstance = case.assertIsInstance
    assertTupleEqual = case.assertTupleEqual
    assertNotEqual = case.assertNotEqual
    assertIsNone = case.assertIsNone
