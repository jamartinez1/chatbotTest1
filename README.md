# Configuración de Google Apps Script para Google Sheets

## ⚠️ IMPORTANTE: URL Incorrecta Detectada

**Error común**: Estás usando la URL de la hoja de cálculo de Google Sheets en lugar de la URL del Apps Script.

❌ **URL INCORRECTA** (lo que pusiste):
```
https://docs.google.com/spreadsheets/d/10N99aO2OCeuWVSL3VkCml_yawDOhVt1QRY9svWWRZKE/edit?gid=0#gid=0
```

✅ **URL CORRECTA** (debe terminar en `/exec`):
```
https://script.google.com/macros/s/TU_SCRIPT_ID_REAL/exec
```

## Pasos para configurar la integración automática:

### 1. Crear Google Apps Script
1. Ve a [Google Apps Script](https://script.google.com/)
2. Crea un nuevo proyecto
3. Copia el contenido del archivo `google_apps_script.js` en el editor
4. Guarda el proyecto

### 2. Vincular con Google Sheets
1. En el Apps Script, ve a "Resources" > "Advanced Google services"
2. Habilita "Google Sheets API"
3. Ve a la hoja de cálculo de Google Sheets (usando el ID en .env)
4. En la hoja, ve a "Extensions" > "Apps Script"
5. Esto vinculará el script con la hoja

### 3. Publicar como Web App
1. En Apps Script, ve a "Publish" > "Deploy as web app"
2. Configura:
   - **Execute the app as**: Me (tu email)
   - **Who has access to the app**: Anyone, even anonymous
3. **Copia la URL generada que termina en `/exec`**

### 4. Actualizar configuración
1. En el archivo `.env`, reemplaza `YOUR_SCRIPT_ID` con el ID real del script:
   ```
   GOOGLE_APPS_SCRIPT_URL=https://script.google.com/macros/s/TU_SCRIPT_ID_REAL/exec
   ```

### 5. Probar la integración
1. Reinicia el servidor backend
2. Realiza una evaluación desde el frontend
3. Verifica que los datos aparezcan en la hoja "Evaluaciones"

## Verificación

Para verificar que la URL es correcta, puedes hacer una petición GET a la URL del Apps Script desde el navegador. Deberías ver algo como:
```json
{
  "status": "Apps Script funcionando",
  "timestamp": "2025-10-15T01:49:17.548Z"
}
```

## Depuración

Si no se registran los datos, revisa los logs del Apps Script:
1. Ve a tu proyecto de Apps Script
2. Ve a "Executions" para ver los logs de ejecución
3. Los logs mostrarán si hay errores en el procesamiento de datos

También puedes probar manualmente con curl:
```bash
curl -X POST https://script.google.com/macros/s/TU_SCRIPT_ID/exec \
  -H "Content-Type: application/json" \
  -d '{"url":"https://test.com","total_score":85.0,"grade":"Excelente"}'
```

## Estructura de la hoja de cálculo

La hoja "Evaluaciones" tendrá las siguientes columnas:
- Timestamp
- URL
- Puntaje Total
- Calificación
- Tipografía
- Color
- Layout
- Usabilidad
- Screenshot URL
- Recomendaciones

## Notas importantes
- La hoja se crea automáticamente con el primer registro
- No se requieren credenciales de API de Google
- El script maneja errores y crea la hoja si no existe
- Los screenshots se almacenan como URLs públicas si se configura Google Drive