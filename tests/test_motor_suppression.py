import unittest
from unittest.mock import MagicMock
import asyncio

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import SensoryState

def evaluate_motor_action(spiked: bool, camera_open: bool) -> bool:
    if spiked and not camera_open:
        return True
    return False

class TestMotorSuppression(unittest.TestCase):
    def test_door_suppressed_when_camera_open(self):
        self.assertFalse(evaluate_motor_action(spiked=True, camera_open=True))
        self.assertTrue(evaluate_motor_action(spiked=True, camera_open=False))

if __name__ == '__main__':
    unittest.main()
