import unittest


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
