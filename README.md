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

## Deployment (Hosting online)

Appen kan hostas på plattformar som Render.com eller Heroku.

### Förutsättningar
- GitHub-repo med `web-upload` branch
- API-nyckel för Gemini (sätt som miljövariabel)

### Render.com (Rekommenderat)
1. Skapa konto på [render.com](https://render.com)
2. Connecta GitHub-repo
3. Välj "Web Service" → Python
4. Start command: `python ifc_analyzer_web.py`
5. Environment: `GEMINI_API_KEY=din_nyckel`
6. Deploy

### Heroku
1. Installera Heroku CLI
2. `heroku create`
3. `git push heroku web-upload:main`
4. `heroku config:set GEMINI_API_KEY=din_nyckel`
5. Öppna appen

### Lokalt test
- Sätt `GEMINI_API_KEY` i miljön
- Kör `python ifc_analyzer_web.py`
