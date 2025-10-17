import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from backend.main import app

client = TestClient(app)

class TestAPI:
    def test_root_endpoint(self):
        """Prueba endpoint raíz"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Herramienta de Evaluación de Diseño Web" in response.json()["message"]

    def test_health_endpoint(self):
        """Prueba endpoint de salud"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "services" in data

    @patch('backend.main.screenshot_capture')
    @patch('backend.main.design_evaluator')
    @patch('backend.main.cloud_storage')
    def test_evaluate_endpoint_success(self, mock_cloud, mock_evaluator, mock_screenshot):
        """Prueba evaluación exitosa"""
        # Mock screenshot
        mock_screenshot.capture_screenshot.return_value = b'fake_image_data'

        # Mock evaluator
        mock_evaluator.evaluate_design.return_value = {
            'total_score': 85.5,
            'grade': 'Excelente',
            'categories': {
                'typography': {'score': 90, 'weight': 0.25},
                'color': {'score': 85, 'weight': 0.25},
                'layout': {'score': 80, 'weight': 0.3},
                'usability': {'score': 88, 'weight': 0.2}
            },
            'recommendations': ['Buen trabajo general']
        }

        # Mock cloud storage
        mock_cloud.upload_screenshot.return_value = 'https://drive.google.com/fake-url'

        response = client.post("/evaluate", json={"url": "https://example.com"})

        assert response.status_code == 200
        data = response.json()

        assert data['url'] == 'https://example.com'
        assert data['total_score'] == 85.5
        assert data['grade'] == 'Excelente'
        assert 'categories' in data
        assert 'recommendations' in data

    def test_evaluate_endpoint_invalid_url(self):
        """Prueba evaluación con URL inválida"""
        response = client.post("/evaluate", json={"url": "invalid-url"})

        assert response.status_code == 400
        assert "URL debe comenzar con http://" in response.json()["detail"]

    def test_evaluate_endpoint_missing_url(self):
        """Prueba evaluación sin URL"""
        response = client.post("/evaluate", json={"url": ""})

        assert response.status_code == 422  # Validation error

    @patch('backend.main.screenshot_capture')
    def test_evaluate_endpoint_screenshot_error(self, mock_screenshot):
        """Prueba manejo de error en captura de screenshot"""
        mock_screenshot.capture_screenshot.side_effect = Exception("Screenshot failed")

        response = client.post("/evaluate", json={"url": "https://example.com"})

        assert response.status_code == 500
        assert "Error interno del servidor" in response.json()["detail"]

    @patch('backend.main.sheets_logger')
    def test_evaluations_endpoint(self, mock_sheets):
        """Prueba obtención de evaluaciones recientes"""
        mock_evaluations = [
            {
                'timestamp': '2024-01-01 10:00:00',
                'url': 'https://example.com',
                'total_score': 85.0,
                'grade': 'Excelente'
            }
        ]
        mock_sheets.get_recent_evaluations.return_value = mock_evaluations

        response = client.get("/evaluations?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert 'evaluations' in data
        assert len(data['evaluations']) == 1

    @patch('backend.main.sheets_logger')
    def test_sheets_url_endpoint(self, mock_sheets):
        """Prueba obtención de URL de Google Sheets"""
        mock_sheets.get_sheet_url.return_value = 'https://docs.google.com/spreadsheets/fake-id'

        response = client.get("/sheets-url")

        assert response.status_code == 200
        data = response.json()
        assert 'sheets_url' in data
        assert 'docs.google.com' in data['sheets_url']