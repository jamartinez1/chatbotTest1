from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import logging
from typing import Optional
import os
import requests
import base64

from .screenshot_capture import ScreenshotCapture
from .cloud_storage import CloudStorage
from .design_evaluator import DesignEvaluator
from .pdf_generator import PDFReportGenerator
from .google_sheets_logger import GoogleSheetsLogger

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
    screenshot_url: Optional[str] = None

class ScreenshotUploadRequest(BaseModel):
    image_base64: str

class ScreenshotUploadResponse(BaseModel):
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None

class EvaluationResponse(BaseModel):
    url: str
    total_score: float
    grade: str
    categories: dict
    recommendations: list
    screenshot_url: Optional[str] = None
    report_url: Optional[str] = None

# Instancias de servicios (se inicializarán cuando sea necesario)
screenshot_capture = None
cloud_storage = None
design_evaluator = None
pdf_generator = PDFReportGenerator()
sheets_logger = None

def initialize_services():
    """Inicializa los servicios externos"""
    global screenshot_capture, cloud_storage, design_evaluator, sheets_logger

    try:
        screenshot_capture = ScreenshotCapture()
        logger.info("Screenshot capture inicializado")

        # Inicializar design_evaluator siempre (no depende de Google)
        design_evaluator = DesignEvaluator()
        logger.info(f"Design evaluator inicializado - OpenAI disponible: {design_evaluator.openai_client is not None}")

        # Inicializar servicios de almacenamiento en la nube (Dropbox por defecto)
        try:
            cloud_storage = CloudStorage()
            logger.info("Almacenamiento en la nube inicializado")
        except Exception as e:
            logger.warning(f"Error inicializando almacenamiento en la nube: {e}")
            cloud_storage = None

        # Solo inicializar servicios de Google si hay credenciales (para Google Sheets)
        creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        if creds_path and os.path.exists(creds_path):
            sheets_logger = GoogleSheetsLogger()

            # Crear hoja si no existe
            if sheets_logger:
                sheets_logger.create_sheet_if_not_exists()
            logger.info("Servicios de Google Sheets inicializados")
        else:
            logger.warning("Credenciales de Google no encontradas. Google Sheets no disponible.")
            sheets_logger = None

    except Exception as e:
        logger.error(f"Error inicializando servicios: {e}")
        import traceback
        logger.error(f"Traceback inicialización: {traceback.format_exc()}")

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    initialize_services()

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {"message": "Herramienta de Evaluación de Diseño Web", "status": "active"}

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_website(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """
    Evalúa el diseño de un sitio web

    - **url**: URL del sitio web a evaluar
    - **screenshot_url**: URL opcional del screenshot ya subido
    """
    url = str(request.url)
    provided_screenshot_url = request.screenshot_url

    try:
        # Validar URL básica
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="URL debe comenzar con http:// o https://")

        # Capturar screenshot
        logger.info(f"Capturando screenshot de {url}")
        screenshot_data = screenshot_capture.capture_screenshot(url)

        # Subir a la nube si está disponible
        screenshot_url = None
        if cloud_storage:
            try:
                logger.info(f"Iniciando subida de screenshot a la nube. Tamaño: {len(screenshot_data)} bytes")
                screenshot_url = cloud_storage.upload_screenshot(screenshot_data, url)
                logger.info(f"Screenshot subido exitosamente: {screenshot_url}")
            except Exception as e:
                logger.error(f"Error subiendo screenshot: {e}")
                import traceback
                logger.error(f"Traceback subida screenshot: {traceback.format_exc()}")

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

        # Usar screenshot_url del request si existe (subido desde frontend), sino el del backend
        final_screenshot_url = provided_screenshot_url or screenshot_url

        # Registrar en Google Sheets en background
        try:
            sheets_logger_instance = GoogleSheetsLogger(
                spreadsheet_id='1Nke_o3A7WdyXKv8Lr9pJv4gpIxBnX0Q3CQCvHn_bOgw',
                apps_script_url='https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec'
            )
            background_tasks.add_task(
                log_evaluation_background,
                url,
                evaluation_data,
                final_screenshot_url,
                sheets_logger_instance
            )
        except Exception as e:
            logger.error(f"Error inicializando Google Sheets logger: {e}")

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

async def log_evaluation_background(url: str, evaluation_data: dict, screenshot_url: str = None, sheets_logger_instance: GoogleSheetsLogger = None):
    """Función en background para registrar evaluación en Google Sheets"""
    try:
        if sheets_logger_instance:
            sheets_logger_instance.log_evaluation(url, evaluation_data, screenshot_url)
            logger.info("Evaluación registrada en Google Sheets")
        else:
            logger.warning("No hay instancia de Google Sheets logger disponible")
    except Exception as e:
        logger.error(f"Error registrando en background: {e}")

@app.get("/evaluations")
async def get_recent_evaluations(limit: int = 10):
    """Obtiene las evaluaciones recientes"""
    try:
        if sheets_logger:
            evaluations = sheets_logger.get_recent_evaluations(limit)
            return {"evaluations": evaluations}
        else:
            return {"evaluations": [], "message": "Google Sheets no configurado"}
    except Exception as e:
        logger.error(f"Error obteniendo evaluaciones: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo evaluaciones")

@app.get("/sheets-url")
async def get_sheets_url():
    """Obtiene la URL de la hoja de Google Sheets"""
    try:
        if sheets_logger:
            return {"sheets_url": sheets_logger.get_sheet_url()}
        else:
            return {"message": "Google Sheets no configurado"}
    except Exception as e:
        logger.error(f"Error obteniendo URL de sheets: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo URL de sheets")

@app.post("/upload-screenshot", response_model=ScreenshotUploadResponse)
async def upload_screenshot(request: ScreenshotUploadRequest):
    """
    Sube un screenshot al Google Apps Script y retorna la URL

    - **image_base64**: Imagen en formato base64 (data:image/png;base64,...)
    """
    try:
        # Obtener la URL del Apps Script desde el entorno
        apps_script_url = os.getenv('GOOGLE_APPS_SCRIPT_URL')
        if not apps_script_url:
            raise HTTPException(status_code=500, detail="GOOGLE_APPS_SCRIPT_URL no configurada")

        # Preparar payload para el Apps Script
        payload = {
            'image_base64': request.image_base64
        }

        logger.info(f"Enviando screenshot al Apps Script. Tamaño: {len(request.image_base64)} caracteres")

        # Enviar POST al Apps Script
        response = requests.post(
            apps_script_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        if result.get('success'):
            screenshot_url = result.get('url')
            logger.info(f"Screenshot subido exitosamente: {screenshot_url}")
            return ScreenshotUploadResponse(success=True, url=screenshot_url)
        else:
            error_msg = result.get('error', 'Error desconocido en Apps Script')
            logger.error(f"Error en Apps Script: {error_msg}")
            return ScreenshotUploadResponse(success=False, error=error_msg)

    except requests.RequestException as e:
        logger.error(f"Error enviando screenshot al Apps Script: {e}")
        raise HTTPException(status_code=500, detail=f"Error al subir screenshot: {str(e)}")
    except Exception as e:
        logger.error(f"Error procesando subida de screenshot: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/health")
async def health_check():
    """Verificación de salud del servicio"""
    services_status = {
        "screenshot_capture": screenshot_capture is not None,
        "cloud_storage": cloud_storage is not None,
        "design_evaluator": design_evaluator is not None,
        "sheets_logger": sheets_logger is not None
    }

    return {
        "status": "healthy" if all(services_status.values()) else "degraded",
        "services": services_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)