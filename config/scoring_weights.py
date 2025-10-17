# Pesos para el cálculo de puntaje de diseño web
SCORING_WEIGHTS = {
    'typography': 0.25,  # Tipografía (legibilidad, tamaño, contraste, jerarquía)
    'color': 0.25,       # Color (armonía, accesibilidad)
    'layout': 0.30,      # Layout (estructura, espacios en blanco)
    'usability': 0.20    # Usabilidad (navegación, interactividad)
}

# Umbrales para calificaciones
SCORE_THRESHOLDS = {
    'excellent': 85,
    'good': 70,
    'fair': 50,
    'poor': 0
}

# Criterios específicos para cada categoría
TYPOGRAPHY_CRITERIA = {
    'font_size': {'min': 14, 'max': 18, 'weight': 0.3},
    'contrast_ratio': {'min': 4.5, 'weight': 0.4},
    'line_height': {'min': 1.2, 'max': 1.6, 'weight': 0.2},
    'hierarchy': {'weight': 0.1}
}

COLOR_CRITERIA = {
    'harmony': {'weight': 0.5},
    'accessibility': {'weight': 0.3},
    'consistency': {'weight': 0.2}
}

LAYOUT_CRITERIA = {
    'whitespace': {'weight': 0.3},
    'structure': {'weight': 0.4},
    'responsiveness': {'weight': 0.3}
}

USABILITY_CRITERIA = {
    'navigation': {'weight': 0.4},
    'interactivity': {'weight': 0.3},
    'performance': {'weight': 0.3}
}