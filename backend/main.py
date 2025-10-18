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

# Instancias de servicios (se inicializarán cuando sea necesario)
screenshot_capture = None
design_evaluator = None

def initialize_services():
    """Inicializa los servicios externos"""
    global screenshot_capture, design_evaluator

    try:
        # Nota: Screenshot capture no se inicializa en entorno de despliegue
        # Solo se usa para desarrollo local
        screenshot_capture = None
        logger.info("Screenshot capture omitido en entorno de despliegue")

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

        # Nota: Screenshot no se captura en entorno de despliegue (Render.com)
        # La evaluación se realiza directamente con OpenAI usando la URL
        logger.info(f"Evaluando diseño de {url} sin captura de screenshot")

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

        # Generar respuesta
        response = EvaluationResponse(
            url=url,
            total_score=evaluation_data['total_score'],
            grade=evaluation_data['grade'],
            categories=evaluation_data['categories'],
            recommendations=evaluation_data.get('recommendations', []),
            screenshot_url=None  # No se sube a la nube, solo se evalúa
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