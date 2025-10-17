import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import requests
from PIL import Image as PILImage

class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()

        # Estilos personalizados
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        )

        self.section_style = ParagraphStyle(
            'Section',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=15
        )

        self.score_style = ParagraphStyle(
            'Score',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=10
        )

    def generate_report(self, evaluation_data: dict, screenshot_url: str, url: str) -> bytes:
        """
        Genera un reporte PDF completo

        Args:
            evaluation_data (dict): Datos de evaluación del diseño
            screenshot_url (str): URL del screenshot en la nube
            url (str): URL original evaluada

        Returns:
            bytes: Datos binarios del PDF generado
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Título
        elements.append(Paragraph("Reporte de Evaluación de Diseño Web", self.title_style))
        elements.append(Spacer(1, 20))

        # Información básica
        elements.append(Paragraph(f"URL Evaluada: {url}", self.styles['Normal']))
        elements.append(Paragraph(f"Fecha de Evaluación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                self.styles['Normal']))
        elements.append(Spacer(1, 20))

        # Puntaje general
        total_score = evaluation_data['total_score']
        grade = evaluation_data['grade']

        elements.append(Paragraph("Puntaje General", self.section_style))
        elements.append(Paragraph(f"<b>{total_score}/100 - {grade}</b>", self.score_style))
        elements.append(Spacer(1, 15))

        # Screenshot
        try:
            elements.append(Paragraph("Captura de Pantalla", self.section_style))
            screenshot_image = self._download_and_resize_image(screenshot_url)
            if screenshot_image:
                elements.append(screenshot_image)
                elements.append(Spacer(1, 20))
        except Exception as e:
            elements.append(Paragraph("Error al cargar screenshot", self.styles['Normal']))
            elements.append(Spacer(1, 10))

        # Desglose por categorías
        elements.append(Paragraph("Desglose por Categorías", self.section_style))

        categories_data = [
            ['Categoría', 'Puntaje', 'Peso', 'Contribución'],
            ['Tipografía', f"{evaluation_data['categories']['typography']['score']}/100",
             f"{evaluation_data['categories']['typography']['weight']*100:.0f}%",
             f"{evaluation_data['categories']['typography']['score'] * evaluation_data['categories']['typography']['weight']:.1f}"],
            ['Color', f"{evaluation_data['categories']['color']['score']}/100",
             f"{evaluation_data['categories']['color']['weight']*100:.0f}%",
             f"{evaluation_data['categories']['color']['score'] * evaluation_data['categories']['color']['weight']:.1f}"],
            ['Layout', f"{evaluation_data['categories']['layout']['score']}/100",
             f"{evaluation_data['categories']['layout']['weight']*100:.0f}%",
             f"{evaluation_data['categories']['layout']['score'] * evaluation_data['categories']['layout']['weight']:.1f}"],
            ['Usabilidad', f"{evaluation_data['categories']['usability']['score']}/100",
             f"{evaluation_data['categories']['usability']['weight']*100:.0f}%",
             f"{evaluation_data['categories']['usability']['score'] * evaluation_data['categories']['usability']['weight']:.1f}"]
        ]

        table = Table(categories_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Recomendaciones
        elements.append(Paragraph("Recomendaciones", self.section_style))
        recommendations = evaluation_data.get('recommendations', [])

        if recommendations:
            for rec in recommendations:
                elements.append(Paragraph(f"• {rec}", self.styles['Normal']))
                elements.append(Spacer(1, 5))
        else:
            elements.append(Paragraph("No hay recomendaciones específicas.", self.styles['Normal']))

        elements.append(Spacer(1, 20))

        # Pie de página
        elements.append(Paragraph("Generado por Herramienta de Evaluación de Diseño Web",
                                ParagraphStyle('Footer', parent=self.styles['Normal'],
                                              fontSize=10, alignment=TA_CENTER)))

        # Generar PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _download_and_resize_image(self, image_url: str) -> Image:
        """
        Descarga y redimensiona una imagen para el PDF

        Args:
            image_url (str): URL de la imagen

        Returns:
            Image: Objeto Image de ReportLab
        """
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Abrir imagen con PIL
            pil_image = PILImage.open(io.BytesIO(response.content))

            # Redimensionar manteniendo proporción
            max_width = 6 * inch
            max_height = 4 * inch

            width, height = pil_image.size
            ratio = min(max_width / width, max_height / height)

            new_width = width * ratio
            new_height = height * ratio

            # Crear buffer para ReportLab
            img_buffer = io.BytesIO()
            pil_image.resize((int(new_width), int(new_height)), PILImage.Resampling.LANCZOS).save(img_buffer, format='PNG')
            img_buffer.seek(0)

            return Image(img_buffer, width=new_width, height=new_height)

        except Exception as e:
            print(f"Error procesando imagen: {e}")
            return None

    def generate_summary_report(self, evaluations: list) -> bytes:
        """
        Genera un reporte resumen de múltiples evaluaciones

        Args:
            evaluations (list): Lista de evaluaciones

        Returns:
            bytes: Datos binarios del PDF resumen
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Título
        elements.append(Paragraph("Resumen de Evaluaciones de Diseño Web", self.title_style))
        elements.append(Spacer(1, 20))

        # Estadísticas generales
        if evaluations:
            avg_score = sum(e['total_score'] for e in evaluations) / len(evaluations)
            elements.append(Paragraph(f"Puntaje Promedio: {avg_score:.1f}/100", self.styles['Normal']))
            elements.append(Paragraph(f"Total de Evaluaciones: {len(evaluations)}", self.styles['Normal']))
            elements.append(Spacer(1, 20))

            # Tabla de evaluaciones
            table_data = [['URL', 'Puntaje', 'Calificación', 'Fecha']]
            for eval_data in evaluations[-10:]:  # Últimas 10 evaluaciones
                table_data.append([
                    eval_data.get('url', 'N/A')[:50] + '...' if len(eval_data.get('url', '')) > 50 else eval_data.get('url', 'N/A'),
                    f"{eval_data['total_score']}/100",
                    eval_data['grade'],
                    eval_data.get('timestamp', 'N/A')
                ])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()