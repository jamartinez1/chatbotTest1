import pytest
from unittest.mock import Mock, patch
from backend.design_evaluator import DesignEvaluator
from config.scoring_weights import SCORING_WEIGHTS

class TestDesignEvaluator:
    def test_initialization_without_credentials(self):
        """Prueba inicialización sin credenciales"""
        with patch.dict('os.environ', {}, clear=True):
            evaluator = DesignEvaluator()
            assert evaluator.client is None

    @patch('backend.design_evaluator.vision.ImageAnnotatorClient')
    def test_initialization_with_credentials(self, mock_client):
        """Prueba inicialización con credenciales"""
        mock_instance = Mock()
        mock_client.return_value = mock_instance

        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json'}):
            evaluator = DesignEvaluator()
            assert evaluator.client == mock_instance

    def test_evaluate_design_fallback(self):
        """Prueba evaluación con datos de respaldo"""
        evaluator = DesignEvaluator()

        # Mock image data
        image_data = b'fake_image_data'

        result = evaluator.evaluate_design(image_data)

        # Verificar estructura de respuesta
        assert 'total_score' in result
        assert 'grade' in result
        assert 'categories' in result
        assert 'recommendations' in result

        # Verificar categorías
        assert 'typography' in result['categories']
        assert 'color' in result['categories']
        assert 'layout' in result['categories']
        assert 'usability' in result['categories']

    @patch('backend.design_evaluator.vision.ImageAnnotatorClient')
    def test_evaluate_design_with_vision(self, mock_client_class):
        """Prueba evaluación con Google Vision"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock vision response
        mock_text_response = Mock()
        mock_text_response.text_annotations = []

        mock_props_response = Mock()
        mock_props_response.image_properties_annotation = Mock()

        mock_client.text_detection.return_value = mock_text_response
        mock_client.image_properties.return_value = mock_props_response

        evaluator = DesignEvaluator()

        # Mock PIL image
        with patch('backend.design_evaluator.Image') as mock_pil_image:
            mock_image_instance = Mock()
            mock_pil_image.open.return_value = mock_image_instance
            mock_image_instance.getcolors.return_value = [(100, (255, 255, 255)), (50, (0, 0, 0))]

            result = evaluator.evaluate_design(b'fake_image_data')

            assert isinstance(result['total_score'], float)
            assert 0 <= result['total_score'] <= 100

    def test_evaluate_typography(self):
        """Prueba evaluación de tipografía"""
        evaluator = DesignEvaluator()

        # Mock vision results
        vision_results = {
            'texts': []
        }

        # Mock PIL image
        mock_pil_image = Mock()

        score = evaluator._evaluate_typography(vision_results, mock_pil_image)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_evaluate_color(self):
        """Prueba evaluación de color"""
        evaluator = DesignEvaluator()

        # Mock PIL image
        mock_pil_image = Mock()
        mock_pil_image.getcolors.return_value = [(100, (255, 255, 255)), (50, (0, 0, 0))]
        mock_pil_image.size = (1920, 1080)

        score = evaluator._evaluate_color(mock_pil_image)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_evaluate_layout(self):
        """Prueba evaluación de layout"""
        evaluator = DesignEvaluator()

        vision_results = {'texts': []}
        mock_pil_image = Mock()
        mock_pil_image.size = (1920, 1080)

        score = evaluator._evaluate_layout(vision_results, mock_pil_image)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_evaluate_usability(self):
        """Prueba evaluación de usabilidad"""
        evaluator = DesignEvaluator()

        vision_results = {'texts': []}

        score = evaluator._evaluate_usability(vision_results)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_generate_recommendations(self):
        """Prueba generación de recomendaciones"""
        evaluator = DesignEvaluator()

        recommendations = evaluator._generate_recommendations(90, 85, 80, 75)
        assert isinstance(recommendations, list)

        # Con puntajes bajos debería generar recomendaciones
        recommendations_low = evaluator._generate_recommendations(40, 30, 50, 45)
        assert len(recommendations_low) > 0
        assert any("tipografía" in rec.lower() or "legibilidad" in rec.lower() for rec in recommendations_low)

    def test_get_grade(self):
        """Prueba asignación de calificaciones"""
        evaluator = DesignEvaluator()

        assert evaluator._get_grade(95) == "Excelente"
        assert evaluator._get_grade(80) == "Bueno"
        assert evaluator._get_grade(60) == "Regular"
        assert evaluator._get_grade(30) == "Necesita mejoras"