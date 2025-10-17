import pytest
import os
from unittest.mock import Mock, patch
from backend.screenshot_capture import ScreenshotCapture

class TestScreenshotCapture:
    def test_initialization(self):
        """Prueba la inicialización del capturador"""
        capture = ScreenshotCapture()
        assert capture.driver is None

    @patch('backend.screenshot_capture.webdriver.Chrome')
    def test_setup_driver(self, mock_chrome):
        """Prueba la configuración del driver"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver

        capture = ScreenshotCapture()
        capture._setup_driver()

        assert capture.driver == mock_driver
        mock_chrome.assert_called_once()

    @patch('backend.screenshot_capture.webdriver.Chrome')
    def test_capture_screenshot_success(self, mock_chrome):
        """Prueba captura exitosa de screenshot"""
        mock_driver = Mock()
        mock_driver.get_screenshot_as_png.return_value = b'fake_png_data'
        mock_chrome.return_value = mock_driver

        capture = ScreenshotCapture()
        result = capture.capture_screenshot('https://example.com')

        assert result == b'fake_png_data'
        mock_driver.get.assert_called_with('https://example.com')
        mock_driver.get_screenshot_as_png.assert_called_once()

    @patch('backend.screenshot_capture.webdriver.Chrome')
    def test_capture_screenshot_with_output_path(self, mock_chrome, tmp_path):
        """Prueba captura con guardado local"""
        mock_driver = Mock()
        mock_driver.get_screenshot_as_png.return_value = b'fake_png_data'
        mock_chrome.return_value = mock_driver

        output_path = tmp_path / "test_screenshot.png"

        capture = ScreenshotCapture()
        result = capture.capture_screenshot('https://example.com', str(output_path))

        assert result == b'fake_png_data'
        assert output_path.exists()

        with open(output_path, 'rb') as f:
            assert f.read() == b'fake_png_data'

    @patch('backend.screenshot_capture.webdriver.Chrome')
    def test_capture_screenshot_error(self, mock_chrome):
        """Prueba manejo de errores en captura"""
        mock_driver = Mock()
        mock_driver.get.side_effect = Exception("Connection failed")
        mock_chrome.return_value = mock_driver

        capture = ScreenshotCapture()

        with pytest.raises(Exception) as exc_info:
            capture.capture_screenshot('https://invalid-url.com')

        assert "Error al capturar screenshot" in str(exc_info.value)

    def test_context_manager(self):
        """Prueba uso como context manager"""
        with ScreenshotCapture() as capture:
            assert hasattr(capture, 'capture_screenshot')
            assert hasattr(capture, 'close')