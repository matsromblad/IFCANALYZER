IFC Analyzer
===============

Ny branch: `web-upload`

## Web-upload funktionalitet
- Flask-app: `ifc_analyzer_web.py`
- Starta: `python ifc_analyzer_web.py`
- URL: `http://localhost:5000`
- Ladda upp `.ifc` fil och få analys-JSON.

## Förutsättningar
- `ifcopenshell` (om IFC-analys krävs)
- `flask`

## Exempel
1. `pip install flask ifcopenshell`
2. `python ifc_analyzer_web.py`
3. Gå till `http://localhost:5000`
4. Välj IFC-fil och klicka "Analysera"
