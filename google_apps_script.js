// Google Apps Script para registrar evaluaciones en Google Sheets y subir screenshots
// Este script debe ser publicado como web app con acceso público

function doPost(e) {
  try {
    // Log para debugging
    Logger.log('doPost called with e: ' + JSON.stringify(e));
    Logger.log('e exists: ' + (e ? 'YES' : 'NO'));
    Logger.log('e.postData exists: ' + (e && e.postData ? 'YES' : 'NO'));
    if (e && e.postData) {
      Logger.log('e.postData.contents exists: ' + (e.postData.contents ? 'YES' : 'NO'));
      Logger.log('e.postData.contents length: ' + (e.postData.contents ? e.postData.contents.length : 0));
    }

    // Verificar que e existe y tiene postData
    if (!e) {
      Logger.log('ERROR: Parameter e is undefined/null');
      throw new Error('Parameter e is undefined - this indicates a deployment or execution issue');
    }

    if (!e.postData) {
      Logger.log('ERROR: e.postData is undefined/null');
      throw new Error('No postData received - check if request is being sent correctly');
    }

    if (!e.postData.contents) {
      Logger.log('ERROR: e.postData.contents is empty');
      throw new Error('postData.contents is empty');
    }

    // Obtener datos del POST
    const data = JSON.parse(e.postData.contents);

    // Verificar si es una petición de screenshot (tiene image_base64)
    if (data.hasOwnProperty('image_base64')) {
      // Manejar subida de screenshot
      Logger.log('Handling screenshot upload');

      try {
        var base64Data = data.image_base64; // Ejemplo: 'data:image/png;base64,iVBORw0...'
        Logger.log('Base64 data length: ' + base64Data.length);

        var matches = base64Data.match(/^data:(.+);base64,(.+)$/);
        if (!matches) {
          throw new Error('Formato de imagen base64 inválido');
        }

        var contentType = matches[1];
        var base64String = matches[2];
        Logger.log('Content type: ' + contentType);
        Logger.log('Base64 string length: ' + base64String.length);

        var bytes = Utilities.base64Decode(base64String);
        Logger.log('Decoded bytes length: ' + bytes.length);

        var blob = Utilities.newBlob(bytes, contentType, 'screenshot.png');
        Logger.log('Blob created successfully');

        // Carpeta destino
        var folderId = '1_Z1vE6Ekg_8-AgEbIcoPsvjitj7_MKyB';
        Logger.log('Attempting to get folder with ID: ' + folderId);

        var folder = DriveApp.getFolderById(folderId);
        Logger.log('Folder obtained successfully: ' + folder.getName());

        var file = folder.createFile(blob);
        Logger.log('File created successfully: ' + file.getName());

        file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
        Logger.log('File sharing set successfully');

        // Construir URL de visualización directa usando el file ID (para mostrar en web)
        var fileId = file.getId();
        var downloadUrl = 'https://drive.google.com/uc?export=view&id=' + fileId;
        Logger.log('Screenshot uploaded successfully: ' + downloadUrl);

      } catch (uploadError) {
        Logger.log('Error during screenshot upload: ' + uploadError.toString());
        throw uploadError; // Re-throw to be caught by outer try-catch
      }

      return ContentService
        .createTextOutput(JSON.stringify({ success: true, url: downloadUrl }))
        .setMimeType(ContentService.MimeType.JSON);
    } else {
      // Manejar registro de evaluación en Sheets
      Logger.log('Handling evaluation logging');

      // Verificar que los datos necesarios estén presentes
      if (!data.url || data.total_score === undefined || data.total_score === null) {
        throw new Error('Datos insuficientes para registrar evaluación: url y total_score son requeridos');
      }

      // Obtener la hoja de cálculo por ID
      const spreadsheet = SpreadsheetApp.openById('1Nke_o3A7WdyXKv8Lr9pJv4gpIxBnX0Q3CQCvHn_bOgw');
      if (!spreadsheet) {
        throw new Error('No se pudo abrir la hoja de cálculo');
      }
      Logger.log('Spreadsheet ID: ' + spreadsheet.getId());

      // Obtener o crear la hoja 'Evaluaciones'
      let sheet = spreadsheet.getSheetByName('Evaluaciones');
      if (!sheet) {
        Logger.log('Creating new sheet: Evaluaciones');
        sheet = spreadsheet.insertSheet('Evaluaciones');

        // Agregar headers
        const headers = [
          'Timestamp',
          'URL',
          'Puntaje Total',
          'Calificación',
          'Tipografía',
          'Color',
          'Layout',
          'Usabilidad',
          'Screenshot URL',
          'Recomendaciones'
        ];
        sheet.appendRow(headers);
        Logger.log('Headers added to new sheet');
      }

      // Preparar fila de datos
      const rowData = [
        data.timestamp || new Date().toISOString(),
        data.url || '',
        data.total_score || 0,
        data.grade || '',
        data.typography_score || 0,
        data.color_score || 0,
        data.layout_score || 0,
        data.usability_score || 0,
        data.screenshot_url || '',
        data.recommendations ? data.recommendations.join('; ') : ''
      ];

      Logger.log('Row data to append: ' + JSON.stringify(rowData));

      // Agregar fila a la hoja
      sheet.appendRow(rowData);

      Logger.log('Evaluation logged successfully');

      // Devolver respuesta de éxito
      return ContentService
        .createTextOutput(JSON.stringify({
          success: true,
          message: 'Evaluación registrada exitosamente',
          timestamp: new Date().toISOString()
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }

  } catch (error) {
    Logger.log('Error in doPost: ' + error.toString());
    // Devolver respuesta de error
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        error: error.toString(),
        timestamp: new Date().toISOString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  // Endpoint GET para verificar que el script funciona
  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'Apps Script funcionando',
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}