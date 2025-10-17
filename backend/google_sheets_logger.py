import os
import logging
import requests
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class GoogleSheetsLogger:
    def __init__(self, spreadsheet_id: str = None, apps_script_url: str = None):
        """
        Inicializa el logger de Google Sheets usando Apps Script

        Args:
            spreadsheet_id (str): ID de la hoja de cálculo de Google Sheets
            apps_script_url (str): URL del Google Apps Script desplegado
        """
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')
        self.apps_script_url = apps_script_url or os.getenv('GOOGLE_APPS_SCRIPT_URL')

        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID es requerido")
        if not self.apps_script_url:
            raise ValueError("Apps Script URL es requerido")

        # Usar la URL del entorno o la proporcionada
        if not self.apps_script_url:
            self.apps_script_url = 'https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec'

        # URL para append data directamente a la hoja pública (solo lectura)
        self.sheets_url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/gviz/tq"

    def log_evaluation(self, url: str, evaluation_data: dict, screenshot_url: str = None):
        """
        Registra una evaluación en Google Sheets vía Apps Script

        Args:
            url (str): URL evaluada
            evaluation_data (dict): Datos de la evaluación
            screenshot_url (str, optional): URL del screenshot
        """
        try:
            # Preparar datos para enviar al Apps Script
            logger.info(f"Enviando datos a Google Sheets: url={url}, score={evaluation_data.get('total_score', 0)}, screenshot_url={screenshot_url}")
            payload = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'total_score': evaluation_data.get('total_score', 0),
                'grade': evaluation_data.get('grade', ''),
                'typography_score': evaluation_data.get('categories', {}).get('typography', {}).get('score', 0),
                'color_score': evaluation_data.get('categories', {}).get('color', {}).get('score', 0),
                'layout_score': evaluation_data.get('categories', {}).get('layout', {}).get('score', 0),
                'usability_score': evaluation_data.get('categories', {}).get('usability', {}).get('score', 0),
                'screenshot_url': screenshot_url or '',
                'recommendations': evaluation_data.get('recommendations', [])
            }
            logger.info(f"Payload completo: {payload}")
            logger.info(f"Payload completo: {payload}")

            # Enviar POST al Apps Script
            response = requests.post(
                self.apps_script_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                logger.info("Evaluación registrada exitosamente en Google Sheets")
            else:
                logger.error(f"Error en Apps Script: {result.get('error', 'Error desconocido')}")
                raise Exception(f"Error al registrar evaluación: {result.get('error', 'Error desconocido')}")

        except requests.RequestException as e:
            logger.error(f"Error enviando datos al Apps Script: {e}")
            raise Exception(f"Error al registrar evaluación: {str(e)}")

    def get_recent_evaluations(self, limit: int = 10) -> list:
        """
        Obtiene las evaluaciones recientes - NO IMPLEMENTADO con Apps Script
        Esta funcionalidad requiere acceso a la API de Google Sheets

        Args:
            limit (int): Número máximo de evaluaciones a obtener

        Returns:
            list: Lista vacía (funcionalidad no disponible)
        """
        logger.warning("get_recent_evaluations no está disponible con Apps Script. Requiere credenciales de API.")
        return []

    def create_sheet_if_not_exists(self):
        """
        Crea la hoja 'Evaluaciones' si no existe - NO IMPLEMENTADO con Apps Script
        La hoja se crea automáticamente cuando se recibe el primer POST
        """
        logger.info("La hoja 'Evaluaciones' se crea automáticamente con el primer registro")

    def get_sheet_url(self) -> str:
        """
        Obtiene la URL pública de la hoja de cálculo

        Returns:
            str: URL de la hoja de Google Sheets
        """
        # Extraer el ID de la hoja del URL del Apps Script
        # El Apps Script URL tiene el formato: https://script.google.com/macros/s/SCRIPT_ID/exec
        # Pero necesitamos el spreadsheet ID. Por ahora devolver un mensaje
        logger.warning("get_sheet_url no disponible sin spreadsheet ID. Configurar GOOGLE_SHEETS_ID en .env")
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
        if spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        else:
            return "URL no disponible - configurar GOOGLE_SHEETS_ID"