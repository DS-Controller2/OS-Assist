import unittest
from unittest.mock import patch
from src.utils import get_current_os # Assuming tests are run from project root

class TestUtils(unittest.TestCase):

    @patch('src.utils.platform.system')
    def test_get_current_os_linux(self, mock_platform_system):
        mock_platform_system.return_value = 'Linux'
        self.assertEqual(get_current_os(), 'linux')

    @patch('src.utils.platform.system')
    def test_get_current_os_windows(self, mock_platform_system):
        mock_platform_system.return_value = 'Windows'
        self.assertEqual(get_current_os(), 'windows')

    @patch('src.utils.platform.system')
    def test_get_current_os_macos(self, mock_platform_system):
        mock_platform_system.return_value = 'Darwin'
        self.assertEqual(get_current_os(), 'macos')

    @patch('src.utils.platform.system')
    def test_get_current_os_unknown(self, mock_platform_system):
        mock_platform_system.return_value = 'JavaOS' # Example of an unknown system
        self.assertEqual(get_current_os(), 'unknown')

    @patch('src.utils.platform.system')
    def test_get_current_os_case_insensitivity(self, mock_platform_system):
        mock_platform_system.return_value = 'LINUX'
        self.assertEqual(get_current_os(), 'linux')
        mock_platform_system.return_value = 'winDOws'
        self.assertEqual(get_current_os(), 'windows')

if __name__ == '__main__':
    unittest.main()
