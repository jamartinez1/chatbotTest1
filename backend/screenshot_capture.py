import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from chromedriver_py import binary_path
from PIL import Image
import io

class ScreenshotCapture:
    def __init__(self):
        self.driver = None

    def _setup_driver(self):
        """Configura el driver de Chrome para captura de screenshots"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Ejecutar en modo headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")  # Resolución estándar
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Opcional: deshabilitar imágenes para velocidad
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        # Especificar la arquitectura correcta para Windows
        chrome_options.add_argument("--arch=x64")

        try:
            # Usar chromedriver-py que incluye el binario
            service = Service(binary_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Error con chromedriver-py: {e}")
            # Fallback: intentar con webdriver-manager
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e2:
                print(f"Error con ChromeDriverManager fallback: {e2}")
                raise Exception(f"No se pudo configurar ChromeDriver: {e2}")

    def capture_screenshot(self, url: str, output_path: str = None) -> bytes:
        """
        Captura screenshot de la URL proporcionada

        Args:
            url (str): URL del sitio web
            output_path (str, optional): Ruta para guardar la imagen localmente

        Returns:
            bytes: Datos de la imagen en formato PNG
        """
        driver = None
        try:
            # Crear un driver nuevo para cada captura
            self._setup_driver()
            driver = self.driver

            driver.get(url)
            # Esperar a que la página cargue completamente
            time.sleep(3)

            # Capturar screenshot
            screenshot = driver.get_screenshot_as_png()

            # Guardar automáticamente en la carpeta screenshots para control
            if not output_path:
                # Crear nombre de archivo basado en la URL y timestamp
                import hashlib
                import datetime
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"screenshots/screenshot_{url_hash}_{timestamp}.png"

            # Guardar localmente
            with open(output_path, 'wb') as f:
                f.write(screenshot)

            return screenshot

        except Exception as e:
            raise Exception(f"Error al capturar screenshot de {url}: {str(e)}")
        finally:
            # Cerrar el driver después de cada uso
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    print(f"Error cerrando driver: {e}")
                self.driver = None

    def capture_full_page(self, url: str, output_path: str = None) -> bytes:
        """
        Captura screenshot de página completa (scroll)

        Args:
            url (str): URL del sitio web
            output_path (str, optional): Ruta para guardar la imagen

        Returns:
            bytes: Datos de la imagen completa
        """
        driver = None
        try:
            # Crear un driver nuevo para cada captura
            self._setup_driver()
            driver = self.driver

            driver.get(url)
            time.sleep(3)

            # Obtener dimensiones totales de la página
            total_width = driver.execute_script("return document.body.scrollWidth")
            total_height = driver.execute_script("return document.body.scrollHeight")

            # Configurar ventana al tamaño total
            driver.set_window_size(total_width, total_height)

            # Capturar screenshot completo
            screenshot = driver.get_screenshot_as_png()

            # Guardar automáticamente en la carpeta screenshots para control
            if not output_path:
                # Crear nombre de archivo basado en la URL y timestamp
                import hashlib
                import datetime
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"screenshots/fullpage_{url_hash}_{timestamp}.png"

            # Guardar localmente
            with open(output_path, 'wb') as f:
                f.write(screenshot)

            return screenshot

        except Exception as e:
            raise Exception(f"Error al capturar página completa de {url}: {str(e)}")
        finally:
            # Cerrar el driver después de cada uso
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    print(f"Error cerrando driver: {e}")
                self.driver = None

    def close(self):
        """Cierra el driver del navegador"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error cerrando driver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()