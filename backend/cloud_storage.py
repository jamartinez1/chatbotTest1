import os
import io
import requests
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class CloudStorage:
    def __init__(self, credentials_path: str = None, folder_id: str = None, apps_script_url: str = None):
        """
        Inicializa el cliente de almacenamiento en la nube usando Google Apps Script

        Args:
            credentials_path (str): Ruta al archivo de credenciales de servicio de Google (fallback)
            folder_id (str): ID de la carpeta de Google Drive donde subir archivos (fallback)
            apps_script_url (str): URL del Google Apps Script para subir screenshots
        """
        self.apps_script_url = apps_script_url or os.getenv('GOOGLE_APPS_SCRIPT_URL')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.folder_id = folder_id or os.getenv('GOOGLE_DRIVE_FOLDER_ID')

        if not self.apps_script_url:
            raise ValueError("Google Apps Script URL es requerido")

        # Inicializar Google Drive como fallback
        if self.credentials_path and os.path.exists(self.credentials_path):
            self.creds = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            self.service = build('drive', 'v3', credentials=self.creds)
            logger.info("Google Drive inicializado como fallback")
        else:
            logger.warning("Credenciales de Google Drive no encontradas - solo Apps Script disponible")

    def upload_image(self, image_data: bytes, filename: str, mime_type: str = 'image/png') -> str:
        """
        Sube una imagen a la nube usando Google Apps Script

        Args:
            image_data (bytes): Datos binarios de la imagen
            filename (str): Nombre del archivo
            mime_type (str): Tipo MIME de la imagen

        Returns:
            str: URL pública del archivo subido
        """
        return self._upload_to_apps_script(image_data, filename, mime_type)

    def _upload_to_apps_script(self, image_data: bytes, filename: str, mime_type: str = 'image/png') -> str:
        """Sube imagen usando Google Apps Script"""
        try:
            # Convertir imagen a base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            data_url = f"data:{mime_type};base64,{base64_data}"

            # Preparar payload para Apps Script
            payload = {
                'image_base64': data_url
            }

            logger.info(f"Iniciando subida a Apps Script: {filename}, tamaño: {len(image_data)} bytes")

            # Enviar POST al Apps Script
            response = requests.post(
                self.apps_script_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            response.raise_for_status()
            result = response.json()
            logger.info(f"Respuesta completa del Apps Script: {result}")

            if result.get('success'):
                public_url = result.get('url')
                if not public_url:
                    logger.error("Apps Script devolvió success=true pero url=None")
                    raise Exception("Apps Script no devolvió URL válida")
                logger.info(f"Imagen subida exitosamente a Apps Script: {public_url}")
                return public_url
            else:
                error_msg = result.get('error', 'Error desconocido en Apps Script')
                logger.error(f"Error en Apps Script: {error_msg}")
                raise Exception(f"Error al subir imagen: {error_msg}")

        except requests.RequestException as e:
            logger.error(f"Error enviando imagen al Apps Script: {e}")
            # Fallback a Google Drive si está disponible
            if hasattr(self, 'service'):
                logger.info("Intentando fallback a Google Drive")
                return self._upload_to_google_drive(image_data, filename, mime_type)
            raise Exception(f"Error al subir imagen: {str(e)}")

    def _upload_to_google_drive(self, image_data: bytes, filename: str, mime_type: str = 'image/png') -> str:
        """Sube imagen a Google Drive (fallback)"""
        try:
            # Crear metadata del archivo
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id] if self.folder_id else []
            }

            # Preparar los datos para subida
            media = MediaIoBaseUpload(
                io.BytesIO(image_data),
                mimetype=mime_type,
                resumable=True
            )

            # Subir archivo
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            file_id = file.get('id')

            # Hacer el archivo público
            self._make_file_public(file_id)

            # Generar URL pública
            public_url = f"https://drive.google.com/uc?id={file_id}"

            logger.info(f"Imagen subida a Google Drive exitosamente: {public_url}")
            return public_url

        except HttpError as e:
            logger.error(f"Error al subir imagen a Google Drive: {e}")
            raise Exception(f"Error al subir imagen: {str(e)}")

    def _make_file_public(self, file_id: str):
        """Hace un archivo público en Google Drive"""
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
        except HttpError as e:
            logger.error(f"Error al hacer archivo público: {e}")
            raise

    def delete_file(self, file_path: str):
        """Elimina un archivo de la nube (no implementado para Apps Script)"""
        logger.warning("Eliminación de archivos no implementada para Google Apps Script")

    def upload_screenshot(self, screenshot_data: bytes, url: str) -> str:
        """
        Sube un screenshot con nombre basado en la URL

        Args:
            screenshot_data (bytes): Datos del screenshot
            url (str): URL original para generar nombre de archivo

        Returns:
            str: URL pública del screenshot
        """
        # Generar nombre de archivo limpio
        import re
        from datetime import datetime

        # Extraer dominio de la URL
        domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain_name = domain.group(1) if domain else 'unknown'

        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"screenshot_{domain_name}_{timestamp}.png"

        return self.upload_image(screenshot_data, filename)
