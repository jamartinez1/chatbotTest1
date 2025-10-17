#!/usr/bin/env python3
"""
Script de prueba para probar el endpoint del Google Apps Script
con subida de screenshots
"""

import requests
import base64
import json
from PIL import Image, ImageDraw
import io

def create_test_image():
    """Crea una imagen de prueba simple"""
    # Crear una imagen de 100x100 píxeles
    img = Image.new('RGB', (100, 100), color='red')
    draw = ImageDraw.Draw(img)

    # Dibujar un círculo blanco en el centro
    draw.ellipse([25, 25, 75, 75], fill='white')

    # Convertir a bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr

def test_apps_script_upload():
    """Prueba la subida de imagen al Apps Script"""

    # URL del Apps Script desde el .env
    apps_script_url = "https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec"

    # Crear imagen de prueba
    image_data = create_test_image()
    print(f"Tamaño de imagen de prueba: {len(image_data)} bytes")

    # Convertir a base64 con formato data URL
    base64_data = base64.b64encode(image_data).decode('utf-8')
    data_url = f"data:image/png;base64,{base64_data}"

    # Preparar payload
    payload = {
        'image_base64': data_url
    }

    print(f"Enviando payload con image_base64 de longitud: {len(data_url)}")
    print(f"Payload keys: {list(payload.keys())}")
    print(f"Primeros 100 caracteres de image_base64: {data_url[:100]}")

    try:
        # Enviar POST
        response = requests.post(
            apps_script_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Respuesta JSON: {json.dumps(result, indent=2)}")

                if result.get('success'):
                    print(f"EXITO! URL del archivo: {result.get('url')}")
                else:
                    print(f"ERROR en Apps Script: {result.get('error')}")

            except json.JSONDecodeError as e:
                print(f"Error decodificando JSON: {e}")
                print(f"Respuesta raw: {response.text}")
        else:
            print(f"Error HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")

    except requests.RequestException as e:
        print(f"Error de conexión: {e}")

def test_apps_script_logging():
    """Prueba el registro en Sheets (sin imagen)"""

    apps_script_url = "https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec"

    # Payload para registro en Sheets
    payload = {
        'timestamp': '2025-01-01T12:00:00Z',
        'url': 'https://example.com',
        'total_score': 85.5,
        'grade': 'Excelente',
        'typography_score': 90,
        'color_score': 80,
        'layout_score': 85,
        'usability_score': 88,
        'screenshot_url': 'https://drive.google.com/test',
        'recommendations': ['Recomendación 1', 'Recomendación 2']
    }

    print("Probando registro en Sheets...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            apps_script_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Respuesta: {json.dumps(result, indent=2)}")

            if result.get('success'):
                print("Registro en Sheets exitoso!")
            else:
                print(f"Error en registro: {result.get('error')}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=== Probando subida de imagen al Apps Script ===")
    test_apps_script_upload()

    print("\n=== Probando registro en Sheets ===")
    test_apps_script_logging()

    print("\n=== Comando cURL para probar manualmente ===")
    print("Para probar la subida de imagen:")
    print('''curl -X POST "https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec" \\
  -H "Content-Type: application/json" \\
  -d '{"image_base64":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAABo0lEQVR4nO3bUU7DQBAEUYy4/5XDh3"}' ''')

    print("\nPara probar el registro en Sheets:")
    print('''curl -X POST "https://script.google.com/macros/s/AKfycbwzdcTEzcs7aNV-JXFh-C4oqNrNA_GNfAmu_WCTwOZjfpmHlliAFP2b_ockFnkd6olY/exec" \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://example.com","total_score":85.5}' ''')