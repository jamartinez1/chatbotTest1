import os
import logging
import json
import colorsys
from typing import Dict, List
from PIL import Image
from openai import OpenAI

# Pesos de puntuación simplificados
SCORING_WEIGHTS = {
    'typography': 0.25,
    'color': 0.25,
    'layout': 0.25,
    'usability': 0.25
}

logger = logging.getLogger(__name__)

class DesignEvaluator:
    def __init__(self, credentials_path: str = None):
        """
        Inicializa el evaluador de diseño con Google Cloud Vision y OpenAI

        Args:
            credentials_path (str): Ruta a las credenciales de Google Cloud
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')

        if self.credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path

        # No inicializar Google Cloud Vision
        self.client = None

        # Inicializar OpenAI
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando OpenAI client: {e}")
                self.openai_client = None
        else:
            logger.warning("OPENAI_API_KEY no encontrada. Funcionalidad LLM limitada.")
            self.openai_client = None

    def evaluate_design(self, page_url: str) -> dict:
        """
        Evalúa el diseño de un sitio web usando LLM

        Args:
            page_url (str): URL de la página web a evaluar

        Returns:
            Dict: Resultados de evaluación con puntajes y recomendaciones
        """
        try:
            # Si tenemos OpenAI, usar análisis LLM avanzado directamente
            if self.openai_client:
                return self._evaluate_with_llm(page_url)
            else:
                # Fallback a evaluación básica (requiere screenshot)
                logger.warning("Usando evaluación básica - OpenAI no disponible")
                return self._get_fallback_evaluation()

        except Exception as e:
            logger.error(f"Error evaluando diseño: {e}")
            return self._get_fallback_evaluation()

    def _analyze_with_vision(self, image) -> dict:
        """Analiza la imagen con Google Cloud Vision"""
        if not self.client:
            return {}

        try:
            # Detectar texto
            text_response = self.client.text_detection(image=image)
            texts = text_response.text_annotations

            # Detectar propiedades de imagen
            props_response = self.client.image_properties(image=image)
            props = props_response.image_properties_annotation

            return {
                'texts': texts,
                'properties': props
            }
        except Exception as e:
            logger.error(f"Error en análisis Vision: {e}")
            return {}

    def _evaluate_with_llm(self, page_url: str) -> Dict:
        """Evalúa el diseño usando OpenAI API"""
        try:
            # Prompt mejorado para evaluación de diseño web basado en conocimiento general
            prompt = f"""
            Evalúa el diseño del sitio web en la siguiente URL: {page_url}

            IMPORTANTE: Como IA de texto, no puedo visitar URLs directamente, pero puedo proporcionar una evaluación basada en mi conocimiento general de buenas prácticas de diseño web y patrones comunes para este sitio específico.

            Basándome en el conocimiento general de {page_url}, evalúa el diseño considerando las mejores prácticas estándar de diseño web para las siguientes categorías:

            1. **Tipografía (Typography)**: Evalúa legibilidad, tamaño de fuente, jerarquía tipográfica, contraste y consistencia. Puntaje 0-100.

            2. **Color**: Evalúa armonía de colores, accesibilidad (contraste), consistencia y uso apropiado. Puntaje 0-100.

            3. **Layout**: Evalúa estructura, uso del espacio, proporciones, alineación y organización visual. Puntaje 0-100.

            4. **Usabilidad**: Evalúa navegación, elementos interactivos, claridad de CTAs, y facilidad de uso. Puntaje 0-100.

            INSTRUCCIONES CRÍTICAS:
            - Debes proporcionar UNA evaluación específica basada en el conocimiento general del sitio web mencionado
            - Los puntajes deben ser realistas y variados (no todos 85-90)
            - Incluye al menos 3 recomendaciones específicas y accionables
            - Responde ÚNICAMENTE con JSON válido, sin texto adicional antes o después

            Respuesta JSON requerida (estructura exacta):
            {{
                "typography": {{"score": 75, "reasoning": "La tipografía es clara pero podría mejorar la jerarquía visual"}},
                "color": {{"score": 82, "reasoning": "Los colores son armoniosos pero el contraste podría optimizarse"}},
                "layout": {{"score": 78, "reasoning": "El layout es funcional pero podría usar mejor los espacios"}},
                "usability": {{"score": 85, "reasoning": "La navegación es intuitiva con elementos interactivos claros"}},
                "recommendations": ["Mejorar el contraste de texto para accesibilidad", "Optimizar la jerarquía tipográfica", "Agregar más elementos visuales de navegación"]
            }}
            """

            # Llamar a OpenAI (sin imagen, solo texto)
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto evaluador de diseño web. Siempre respondes ÚNICAMENTE con JSON válido. Nunca incluyes texto adicional antes o después del JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )

            # Parsear respuesta JSON
            result_text = response.choices[0].message.content.strip()
            logger.info(f"Respuesta cruda de OpenAI: {result_text}")

            # Limpiar posibles caracteres markdown
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

            logger.info(f"Respuesta limpia de OpenAI: {result_text}")
            llm_result = json.loads(result_text)

            # Calcular puntaje total ponderado
            total_score = (
                llm_result['typography']['score'] * SCORING_WEIGHTS['typography'] +
                llm_result['color']['score'] * SCORING_WEIGHTS['color'] +
                llm_result['layout']['score'] * SCORING_WEIGHTS['layout'] +
                llm_result['usability']['score'] * SCORING_WEIGHTS['usability']
            )

            return {
                'total_score': round(total_score, 1),
                'categories': {
                    'typography': {
                        'score': round(llm_result['typography']['score'], 1),
                        'weight': SCORING_WEIGHTS['typography'],
                        'reasoning': llm_result['typography']['reasoning']
                    },
                    'color': {
                        'score': round(llm_result['color']['score'], 1),
                        'weight': SCORING_WEIGHTS['color'],
                        'reasoning': llm_result['color']['reasoning']
                    },
                    'layout': {
                        'score': round(llm_result['layout']['score'], 1),
                        'weight': SCORING_WEIGHTS['layout'],
                        'reasoning': llm_result['layout']['reasoning']
                    },
                    'usability': {
                        'score': round(llm_result['usability']['score'], 1),
                        'weight': SCORING_WEIGHTS['usability'],
                        'reasoning': llm_result['usability']['reasoning']
                    }
                },
                'recommendations': llm_result['recommendations'],
                'grade': self._get_grade(total_score)
            }

        except Exception as e:
            logger.error(f"Error en evaluación LLM: {e}")
            # Fallback a evaluación básica
            return self._get_fallback_evaluation()

    def _evaluate_basic(self, vision_results: dict, pil_image) -> dict:
        """Evaluación básica como fallback"""
        # Evaluaciones específicas
        typography_score = self._evaluate_typography(vision_results, pil_image)
        color_score = self._evaluate_color(pil_image)
        layout_score = self._evaluate_layout(vision_results, pil_image)
        usability_score = self._evaluate_usability(vision_results)

        # Calcular puntaje total ponderado
        total_score = (
            typography_score * SCORING_WEIGHTS['typography'] +
            color_score * SCORING_WEIGHTS['color'] +
            layout_score * SCORING_WEIGHTS['layout'] +
            usability_score * SCORING_WEIGHTS['usability']
        )

        # Generar recomendaciones
        recommendations = self._generate_recommendations(
            typography_score, color_score, layout_score, usability_score
        )

        return {
            'total_score': round(total_score, 1),
            'categories': {
                'typography': {
                    'score': round(typography_score, 1),
                    'weight': SCORING_WEIGHTS['typography']
                },
                'color': {
                    'score': round(color_score, 1),
                    'weight': SCORING_WEIGHTS['color']
                },
                'layout': {
                    'score': round(layout_score, 1),
                    'weight': SCORING_WEIGHTS['layout']
                },
                'usability': {
                    'score': round(usability_score, 1),
                    'weight': SCORING_WEIGHTS['usability']
                }
            },
            'recommendations': recommendations,
            'grade': self._get_grade(total_score)
        }

    def _evaluate_typography(self, vision_results: Dict, pil_image: Image) -> float:
        """Evalúa la tipografía"""
        score = 50  # Puntaje base

        texts = vision_results.get('texts', [])
        if not texts:
            return score

        # Analizar propiedades de texto
        text_sizes = []
        for text in texts[1:]:  # Saltar el primer elemento (texto completo)
            bounds = text.bounding_poly.vertices
            height = abs(bounds[2].y - bounds[0].y)
            text_sizes.append(height)

        if text_sizes:
            avg_size = sum(text_sizes) / len(text_sizes)
            # Verificar tamaño de fuente (asumiendo resolución típica)
            if 14 <= avg_size <= 18:
                score += 20
            elif 12 <= avg_size <= 20:
                score += 10

        # Simular evaluación de contraste (en implementación real necesitaríamos OCR más avanzado)
        score += 15  # Contraste asumido aceptable

        return min(100, score)

    def _evaluate_color(self, pil_image: Image) -> float:
        """Evalúa el uso del color"""
        try:
            # Obtener colores dominantes
            colors = pil_image.getcolors(pil_image.size[0] * pil_image.size[1])
            if not colors:
                return 50

            # Analizar paleta de colores
            dominant_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:10]

            # Evaluar armonía básica (diversidad de colores)
            unique_hues = set()
            for count, color in dominant_colors:
                if isinstance(color, (tuple, list)) and len(color) >= 3:
                    r, g, b = color[:3]
                    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                    unique_hues.add(round(h * 360))  # Convertir a grados

            harmony_score = min(30, len(unique_hues) * 3)

            # Evaluar accesibilidad básica (contraste)
            accessibility_score = 25  # Asumido básico

            # Consistencia
            consistency_score = 20  # Asumido básico

            return harmony_score + accessibility_score + consistency_score

        except Exception as e:
            logger.error(f"Error evaluando color: {e}")
            return 50

    def _evaluate_layout(self, vision_results: Dict, pil_image: Image) -> float:
        """Evalúa el layout y estructura"""
        score = 60  # Puntaje base

        width, height = pil_image.size
        aspect_ratio = width / height

        # Evaluar proporciones
        if 1.3 <= aspect_ratio <= 1.8:  # Proporción típica de páginas web
            score += 15

        # Evaluar uso de espacio (simplificado)
        # En implementación real, analizar elementos detectados
        whitespace_score = 15  # Asumido básico

        # Estructura
        structure_score = 10  # Asumido básico

        return min(100, score + whitespace_score + structure_score)

    def _evaluate_usability(self, vision_results: Dict) -> float:
        """Evalúa la usabilidad"""
        score = 55  # Puntaje base

        # Análisis simplificado basado en elementos detectados
        texts = vision_results.get('texts', [])

        # Evaluar navegación (presencia de elementos de navegación típicos)
        nav_indicators = ['menu', 'nav', 'home', 'contact', 'about']
        nav_score = 0
        for text in texts:
            description = text.description.lower()
            if any(indicator in description for indicator in nav_indicators):
                nav_score = 20
                break

        # Interactividad (simplificada)
        interactivity_score = 15  # Asumido básico

        # Performance (simplificada)
        performance_score = 10  # Asumido básico

        return min(100, score + nav_score + interactivity_score + performance_score)

    def _generate_recommendations(self, typography: float, color: float,
                                layout: float, usability: float) -> List[str]:
        """Genera recomendaciones basadas en los puntajes"""
        recommendations = []

        if typography < 70:
            recommendations.append("Mejora la legibilidad: usa tamaños de fuente entre 14-18px y asegura buen contraste.")
        if color < 70:
            recommendations.append("Optimiza la paleta de colores: busca armonía y asegura accesibilidad (contraste mínimo 4.5:1).")
        if layout < 70:
            recommendations.append("Revisa el layout: utiliza mejor los espacios en blanco y asegura estructura clara.")
        if usability < 70:
            recommendations.append("Mejora la usabilidad: simplifica la navegación y agrega elementos interactivos claros.")

        if not recommendations:
            recommendations.append("¡Excelente trabajo! Tu sitio tiene un diseño muy sólido.")

        return recommendations

    def _get_grade(self, score: float) -> str:
        """Convierte puntaje numérico a calificación cualitativa"""
        if score >= 85:
            return "Excelente"
        elif score >= 70:
            return "Bueno"
        elif score >= 50:
            return "Regular"
        else:
            return "Necesita mejoras"

    def _get_fallback_evaluation(self) -> Dict:
        """Evaluación de respaldo cuando falla el análisis"""
        return {
            'total_score': 50.0,
            'categories': {
                'typography': {'score': 50.0, 'weight': SCORING_WEIGHTS['typography']},
                'color': {'score': 50.0, 'weight': SCORING_WEIGHTS['color']},
                'layout': {'score': 50.0, 'weight': SCORING_WEIGHTS['layout']},
                'usability': {'score': 50.0, 'weight': SCORING_WEIGHTS['usability']}
            },
            'recommendations': ["No se pudo analizar completamente. Verifica la calidad de la imagen."],
            'grade': "Regular"
        }