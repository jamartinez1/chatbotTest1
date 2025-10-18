from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import logging
from typing import Optional
import os
import requests
import base64

from .screenshot_capture import ScreenshotCapture
from .design_evaluator import DesignEvaluator

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Herramienta de Evaluación de Diseño Web", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class EvaluationRequest(BaseModel):
    url: HttpUrl

class EvaluationResponse(BaseModel):
    url: str
    total_score: float
    grade: str
    categories: dict
    recommendations: list
    screenshot_url: Optional[str] = None

# Instancias de servicios (se inicializarán cuando sea necesario)
screenshot_capture = None
design_evaluator = None

def upload_screenshot_to_drive(screenshot_data):
    """
    Sube un screenshot a Google Drive usando Apps Script

    Args:
        screenshot_data: Bytes del screenshot

    Returns:
        str: URL del archivo subido en Google Drive
    """
    try:
        # URL del Apps Script (debe estar configurada en el .env)
        apps_script_url = os.getenv('GOOGLE_APPS_SCRIPT_URL')
        logger.info(f"Usando Apps Script URL: {apps_script_url}")

        # Convertir bytes a base64
        base64_data = base64.b64encode(screenshot_data).decode('utf-8')
        data_url = f"data:image/png;base64,{base64_data}"
        logger.info(f"Imagen base64 preparada, tamaño: {len(base64_data)} caracteres")

        # Preparar payload para Apps Script
        payload = {
            'image_base64': data_url
        }

        # Enviar POST al Apps Script
        logger.info("Enviando solicitud POST al Apps Script...")
        response = requests.post(
            apps_script_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        logger.info(f"Respuesta del Apps Script - Status: {response.status_code}")
        response.raise_for_status()

        result = response.json()
        logger.info(f"Respuesta JSON del Apps Script: {result}")

        if not result.get('success'):
            raise Exception(f"Apps Script error: {result.get('error', 'Unknown error')}")

        screenshot_url = result.get('url')
        logger.info(f"Screenshot subido exitosamente: {screenshot_url}")
        return screenshot_url

    except Exception as e:
        logger.error(f"Error subiendo screenshot a Drive: {e}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        raise

def register_evaluation_in_sheets(url, evaluation_data, screenshot_url):
    """
    Registra la evaluación en Google Sheets usando Apps Script

    Args:
        url: URL evaluada
        evaluation_data: Datos de la evaluación
        screenshot_url: URL del screenshot (opcional)
    """
    try:
        # URL del Apps Script (debe estar configurada en el .env)
        apps_script_url = os.getenv('GOOGLE_APPS_SCRIPT_URL')
        logger.info(f"Registrando evaluación en Sheets usando URL: {apps_script_url}")

        # Preparar payload para registro en Sheets
        recommendations = evaluation_data.get('recommendations', [])
        if not isinstance(recommendations, list):
            recommendations = [str(recommendations)]

        payload = {
            'timestamp': evaluation_data.get('timestamp', '2025-01-01T12:00:00Z'),
            'url': url,
            'total_score': evaluation_data['total_score'],
            'grade': evaluation_data['grade'],
            'typography_score': evaluation_data.get('categories', {}).get('typography', {}).get('score', 0),
            'color_score': evaluation_data.get('categories', {}).get('color', {}).get('score', 0),
            'layout_score': evaluation_data.get('categories', {}).get('layout', {}).get('score', 0),
            'usability_score': evaluation_data.get('categories', {}).get('usability', {}).get('score', 0),
            'screenshot_url': screenshot_url or '',
            'recommendations': recommendations
        }

        logger.info(f"Payload para Sheets: {payload}")

        # Enviar POST al Apps Script
        response = requests.post(
            apps_script_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        logger.info(f"Respuesta Sheets - Status: {response.status_code}")
        response.raise_for_status()

        result = response.json()
        logger.info(f"Respuesta JSON Sheets: {result}")

        if not result.get('success'):
            raise Exception(f"Apps Script error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error registrando en Sheets: {e}")
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")
        raise

def initialize_services():
    """Inicializa los servicios externos"""
    global screenshot_capture, design_evaluator

    try:
        screenshot_capture = ScreenshotCapture()
        logger.info("Screenshot capture inicializado")

        # Inicializar design_evaluator siempre (no depende de Google)
        design_evaluator = DesignEvaluator()
        logger.info(f"Design evaluator inicializado - OpenAI disponible: {design_evaluator.openai_client is not None}")

    except Exception as e:
        logger.error(f"Error inicializando servicios: {e}")
        import traceback
        logger.error(f"Traceback inicialización: {traceback.format_exc()}")

# Montar archivos estáticos del frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    initialize_services()

@app.get("/")
async def root():
    """Servir el frontend React"""
    return FileResponse("index.html", media_type="text/html")

@app.get("/api/")
async def api_root():
    """Endpoint raíz de la API"""
    return {"message": "Herramienta de Evaluación de Diseño Web API", "status": "active"}

@app.post("/api/evaluate", response_model=EvaluationResponse)
async def evaluate_website(request: EvaluationRequest):
    """
    Evalúa el diseño de un sitio web

    - **url**: URL del sitio web a evaluar
    """
    url = str(request.url)

    try:
        # Validar URL básica
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")

        # Capturar screenshot
        logger.info(f"Capturando screenshot de {url}")
        screenshot_data = screenshot_capture.capture_screenshot(url)

        # Subir screenshot a Google Drive usando Apps Script
        screenshot_url = None
        try:
            logger.info("Subiendo screenshot a Google Drive...")
            screenshot_url = upload_screenshot_to_drive(screenshot_data)
            logger.info(f"Screenshot subido exitosamente: {screenshot_url}")
        except Exception as e:
            logger.error(f"Error subiendo screenshot a Drive: {e}")
            # Continuar sin screenshot_url si falla la subida

        # Evaluar diseño
        logger.info(f"Estado de servicios - design_evaluator: {design_evaluator is not None}")
        evaluation_data = {"total_score": 50.0, "grade": "Regular", "categories": {}, "recommendations": ["Evaluación básica completada"]}

        if design_evaluator:
            try:
                logger.info(f"Iniciando evaluación de diseño para: {url}")
                # OpenAI evalúa directamente la URL de la página
                evaluation_data = design_evaluator.evaluate_design(url)
                logger.info(f"Evaluación completada: {evaluation_data['total_score']}/100")
                logger.info(f"Detalles evaluación: {evaluation_data}")
            except Exception as e:
                logger.error(f"Error en evaluación de diseño: {e}")
                import traceback
                logger.error(f"Traceback completo: {traceback.format_exc()}")
        else:
            logger.warning("Design evaluator no está disponible - usando evaluación básica")

        # Registrar evaluación en Google Sheets
        try:
            logger.info("Registrando evaluación en Google Sheets...")
            register_evaluation_in_sheets(url, evaluation_data, screenshot_url)
            logger.info("Evaluación registrada exitosamente en Sheets")
        except Exception as e:
            logger.error(f"Error registrando en Sheets: {e}")
            # Continuar aunque falle el registro en Sheets

        # Generar respuesta
        response = EvaluationResponse(
            url=url,
            total_score=evaluation_data['total_score'],
            grade=evaluation_data['grade'],
            categories=evaluation_data['categories'],
            recommendations=evaluation_data.get('recommendations', []),
            screenshot_url=screenshot_url
        )

        return response

    except Exception as e:
        logger.error(f"Error procesando evaluación: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Verificación de salud del servicio"""
    services_status = {
        "screenshot_capture": screenshot_capture is not None,
        "design_evaluator": design_evaluator is not None
    }

    return {
        "status": "healthy" if all(services_status.values()) else "degraded",
        "services": services_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)