IFC Analyzer
===============

# IFC Analyzer Web

A comprehensive web-based IFC (Industry Foundation Classes) model analyzer with advanced features for BIM professionals and developers.

## Features

### 🔍 **Core Analysis Capabilities**
- **Entity Analysis**: Count and categorize all IFC entities in your model
- **Geometry Analysis**: Identify heavy geometry objects that may impact performance
- **Orphan Detection**: Find orphaned objects with optional deep checking
- **Header Metadata**: Extract and display IFC file header information
- **Schema Detection**: Automatic IFC schema version detection

### 🌐 **Web Interface Features**
- **Drag & Drop Upload**: Intuitive file upload with visual feedback
- **Batch Processing**: Upload and analyze multiple IFC files simultaneously
- **Real-time Progress**: Live upload and analysis progress tracking
- **Dark Mode**: Toggle between light and dark themes
- **Mobile Responsive**: Optimized for tablets and smartphones
- **Error Handling**: Comprehensive error messages with retry mechanisms

### 🤖 **AI-Powered Insights**
- **Smart Recommendations**: AI-generated suggestions for IFC export optimization
- **Exporter Detection**: Automatic detection of IFC export software
- **Performance Tips**: Recommendations for file cleanup and optimization

### 📊 **Results & Export**
- **Comprehensive Reports**: Detailed HTML reports with tables and summaries
- **JSON Export**: Download complete analysis data as JSON
- **Visual Summaries**: Easy-to-read entity type breakdowns and statistics

## Analysis Options

### Deep Orphan Check
The deep orphan check performs a thorough analysis of orphaned objects in IFC models:

- **What it does**: Analyzes all relationships and references in the IFC file to identify truly orphaned objects
- **When to use**: Enable for complex models or when standard orphan detection misses issues
- **Performance impact**: Increases analysis time but provides more comprehensive results
- **Use case**: Quality assurance, model cleanup, identifying potential data integrity issues

## Quick Start

### Local Development
```bash
# Install dependencies
pip install flask ifcopenshell ifctester

# Set API key (optional, for AI recommendations)
export GEMINI_API_KEY="your_api_key_here"

# Run the web app
python ifc_analyzer_web.py

# Open in browser
# http://localhost:5000
```

### Online Deployment
The app is ready for deployment on platforms like Render.com, Heroku, or any Python hosting service.

## Usage

1. **Upload Files**: Drag & drop IFC files or click to browse
2. **Configure Options**: Enable deep orphan checking for thorough analysis (slower but more comprehensive)
3. **Analyze**: Click "Analyze" to process your files
4. **Review Results**: View comprehensive analysis in the web interface
5. **Download**: Export JSON reports for further processing

## Technical Details

- **Backend**: Python Flask web framework
- **IFC Processing**: ifcopenshell and ifctester libraries
- **AI Integration**: Google Gemini API for intelligent recommendations
- **Frontend**: Vanilla HTML/CSS/JavaScript with responsive design
- **File Support**: .ifc, .ifczip, .ifcz files up to 1GB each
- **Batch Support**: Multiple file analysis with combined results

## API Environment Variables

- `GEMINI_API_KEY`: Google Gemini API key for AI recommendations (optional)
- `PORT`: Server port (defaults to 5000)

---

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
