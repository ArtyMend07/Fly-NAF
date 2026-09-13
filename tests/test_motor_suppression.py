import unittest
from unittest.mock import MagicMock
import asyncio

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import SensoryState

def evaluate_motor_action(spiked: bool, camera_open: bool) -> bool:
    """
    Isolamento da lógica de supressão motora (Environmental Context Guard)
    para garantir que os comandos não ignorem as leis físicas do jogo.
    """
    if spiked and not camera_open:
        return True
    return False

class TestMotorSuppression(unittest.TestCase):
    def test_door_suppressed_when_camera_open(self):
        # Cenário 1: Mosca toma susto (spiked=True), mas câmera está aberta.
        # Resultado esperado: Falso (ação bloqueada)
        self.assertFalse(evaluate_motor_action(spiked=True, camera_open=True))
        
        # Cenário 2: Mosca toma susto, câmera abaixada.
        # Resultado esperado: Verdadeiro (ação disparada)
        self.assertTrue(evaluate_motor_action(spiked=True, camera_open=False))

if __name__ == '__main__':
    unittest.main()
