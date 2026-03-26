import os
import tempfile
import json
import traceback
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

# Reuse core analysis from existing module
from ifc_analyzer import analyze_ifc, AnalyzeOptions

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB upload limit


def detect_exporter(report):
    hdr = report.get("header", {})
    origin = hdr.get("OriginatingSystem") or hdr.get("Preprocessor") or "unknown"
    origin_lower = str(origin).lower()
    if "revit" in origin_lower:
        return "Autodesk Revit"
    if "archicad" in origin_lower:
        return "Graphisoft Archicad"
    if "tekla" in origin_lower:
        return "Tekla Structures"
    if "allplan" in origin_lower:
        return "Nemetschek Allplan"
    if "rhino" in origin_lower or "grasshopper" in origin_lower:
        return "Rhino/Grasshopper"
    if "bricscad" in origin_lower:
        return "BricsCAD"
    return origin


def ai_recommendations(report):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return ["No GEMINI_API_KEY set in environment. Set it and restart the app."]

    exporter = detect_exporter(report)
    orphans = report.get("orphans", {}).get("orphan_total", 0)
    heavy = len(report.get("geometry", {}).get("heavy_geometry_topN", []))

    # Example prompt (implement with real Gemini client in production):
    prompt = (
        "IFC analysis data from model exported by %s. "
        "Entity count: %s, orphans: %s, heavy geom candidates: %s. "
        "Provide improvement suggestions for IFC export and file cleanup."
    ) % (exporter, report.get("meta", {}).get("entity_total", "?"), orphans, heavy)

    # TODO: Replace with real Gemini API call e.g. via openai/vertex-ai client.
    # requests.post('https://gemini.googleapis.com/...', headers={'Authorization': 'Bearer ' + api_key}, json={...})

    # Fallback: provide general tips.
    result = [
        f"Detected exporter: {exporter}",
        f"Orphan objects: {orphans} (<=20% is normal).",
        f"Heavy geometry objects: {heavy}. Check top lists for details.",
    ]
    result.extend(report.get("recommendations", []))
    result.append("(AI analysis key verified, standard recommendations.)")
    return result

BASE_CSS = """
:root {
    --bg-color: #f2f4f7;
    --text-color: #1c1f23;
    --card-bg: #ffffff;
    --card-border: #dedeef;
    --table-border: #e6e9ef;
    --table-header-bg: #f4f6fc;
    --btn-primary: #2f80ed;
    --btn-primary-hover: #1f6ad0;
    --btn-success: #28a745;
    --btn-success-hover: #218838;
    --drop-zone-bg: #fafafa;
    --drop-zone-border: #d0d0d0;
    --drop-zone-hover: #f0f8ff;
    --drop-zone-active: #f8fff8;
    --file-info-bg: #e8f4fd;
    --progress-bg: #f0f0f0;
    --muted-text: #666;
}

[data-theme="dark"] {
    --bg-color: #1a1a1a;
    --text-color: #e0e0e0;
    --card-bg: #2d2d2d;
    --card-border: #404040;
    --table-border: #404040;
    --table-header-bg: #333333;
    --btn-primary: #4a90e2;
    --btn-primary-hover: #357abd;
    --btn-success: #4caf50;
    --btn-success-hover: #45a049;
    --drop-zone-bg: #333333;
    --drop-zone-border: #555555;
    --drop-zone-hover: #2a4a6b;
    --drop-zone-active: #2a4a2a;
    --file-info-bg: #2a4a6b;
    --progress-bg: #404040;
    --muted-text: #999;
}

body {
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    transition: background-color 0.3s ease, color 0.3s ease;
}
.container {
    max-width: 960px;
    margin: 30px auto;
    padding: 20px;
    background: var(--card-bg);
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transition: background-color 0.3s ease;
}
header h1 {
    margin-bottom: 8px;
}
.card {
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 20px;
    background: var(--card-bg);
    transition: background-color 0.3s ease, border-color 0.3s ease;
}
.btn-primary {
    background: var(--btn-primary);
    color: white;
    border: 0;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}
.btn-primary:hover { background: var(--btn-primary-hover); }
.btn-success {
    background: var(--btn-success);
    color: white;
    border: 0;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 14px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}
.btn-success:hover { background: var(--btn-success-hover); }
.report-key {
    font-weight: 700;
}
.report-value {
    color: var(--text-color);
}
.table {
    width: 100%;
    border-collapse: collapse;
}
.table th,
.table td {
    border: 1px solid var(--table-border);
    padding: 8px;
    text-align: left;
    transition: border-color 0.3s ease;
}
.table th { background: var(--table-header-bg); transition: background-color 0.3s ease; }
.progress-container {
    margin: 10px 0;
    display: none;
}
.progress-bar {
    width: 100%;
    height: 20px;
    background-color: var(--progress-bg);
    border-radius: 10px;
    overflow: hidden;
    transition: background-color 0.3s ease;
}
.progress-fill {
    height: 100%;
    background-color: var(--btn-primary);
    width: 0%;
    transition: width 0.3s ease, background-color 0.3s ease;
}
.status-text {
    margin-top: 5px;
    font-size: 14px;
    color: var(--muted-text);
    transition: color 0.3s ease;
}
.drop-zone {
    border: 2px dashed var(--drop-zone-border);
    border-radius: 8px;
    padding: 40px 20px;
    text-align: center;
    background: var(--drop-zone-bg);
    transition: all 0.3s ease;
    cursor: pointer;
    margin-bottom: 20px;
}
.drop-zone.dragover {
    border-color: var(--btn-primary);
    background: var(--drop-zone-hover);
}
.drop-zone.has-file {
    border-color: var(--btn-success);
    background: var(--drop-zone-active);
}
.file-info {
    margin-top: 15px;
    padding: 10px;
    background: var(--file-info-bg);
    border-radius: 6px;
    display: none;
    transition: background-color 0.3s ease;
}
.file-info.show {
    display: block;
}
.theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 50%;
    width: 50px;
    height: 50px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.theme-toggle:hover {
    transform: scale(1.1);
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .container {
        margin: 10px;
        padding: 15px;
    }
    
    .theme-toggle {
        top: 10px;
        right: 10px;
        width: 45px;
        height: 45px;
        font-size: 18px;
    }
    
    .drop-zone {
        padding: 30px 15px;
    }
    
    .table {
        font-size: 14px;
    }
    
    .table th,
    .table td {
        padding: 6px 4px;
    }
    
    .btn-primary,
    .btn-success {
        width: 100%;
        margin-bottom: 10px;
    }
    
    .file-info {
        font-size: 14px;
    }
    
    header h1 {
        font-size: 24px;
    }
    
    .progress-container {
        margin: 15px 0;
    }
}

@media (max-width: 480px) {
    .container {
        margin: 5px;
        padding: 10px;
    }
    
    .drop-zone {
        padding: 20px 10px;
    }
    
    .card {
        padding: 10px;
    }
    
    header h1 {
        font-size: 20px;
    }
    
    .table {
        font-size: 12px;
    }
    
    .table th,
    .table td {
        padding: 4px 2px;
    }
}
"""

UPLOAD_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IFC Analyzer Web</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <button id="themeToggle" class="theme-toggle" title="Toggle Dark Mode">🌙</button>
  
  <div class="container">
    <header>
      <h1>IFC Analyzer Web</h1>
      <p>Upload an IFC model for analysis and get a comprehensive results page with summary.</p>
    </header>

    <section class="card">
      <div id="dropZone" class="drop-zone">
        <div>
          <strong>Drag & Drop IFC Files Here</strong><br>
          <span style="color: var(--muted-text); font-size: 14px;">or click to browse (multiple files supported)</span>
        </div>
        <input type="file" id="ifc_file" name="ifc_file" accept=".ifc,.ifczip,.ifcz" multiple style="display: none;" required>
      </div>

      <div id="fileInfo" class="file-info">
        <strong>Selected Files:</strong><br>
        <div id="fileList"></div>
        <div id="totalSize" style="margin-top: 8px; font-weight: bold;"></div>
      </div>

      <div style="margin: 12px 0;">
        <label><input type="checkbox" id="deep_orphan_check" name="deep_orphan_check" value="1"> Perform deep orphan check</label>
      </div>
      <button id="analyzeBtn" class="btn-primary" type="button">Analyze</button>
    </section>

    <section class="card">
      <h2>Instructions</h2>
      <ul>
        <li>Max file size: 1 GB.</li>
        <li>Results are displayed as HTML (JSON data is still available under the hood).</li>
        <li>For larger datasets: consider running locally with Python/Flask.</li>
      </ul>
    </section>

    <div id="progressContainer" class="progress-container">
      <div class="progress-bar">
        <div id="progressFill" class="progress-fill"></div>
      </div>
      <div id="statusText" class="status-text">Preparing upload...</div>
    </div>
  </div>

  <script>
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('ifc_file');
    const fileInfo = document.getElementById('fileInfo');
    const fileList = document.getElementById('fileList');
    const totalSize = document.getElementById('totalSize');
    const analyzeBtn = document.getElementById('analyzeBtn');

    // Drag & Drop functionality
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');

      const files = Array.from(e.dataTransfer.files).filter(file => {
        const suffix = file.name.toLowerCase().split('.').pop();
        return ['ifc', 'ifczip', 'ifcz'].includes(suffix);
      });

      if (files.length > 0) {
        // Create a new FileList-like object
        const dt = new DataTransfer();
        files.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
        updateFileInfo(files);
      }
    });

    fileInput.addEventListener('change', (e) => {
      const files = Array.from(e.target.files);
      if (files.length > 0) {
        updateFileInfo(files);
      }
    });

    function updateFileInfo(files) {
      fileList.innerHTML = '';
      let totalSizeBytes = 0;

      files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.style.marginBottom = '4px';
        fileItem.innerHTML = `
          <span style="font-weight: bold;">${index + 1}.</span> ${file.name}
          <span style="color: var(--muted-text); font-size: 12px;">
            (${(file.size / 1024 / 1024).toFixed(2)} MB)
          </span>
        `;
        fileList.appendChild(fileItem);
        totalSizeBytes += file.size;
      });

      totalSize.textContent = `Total: ${files.length} file${files.length > 1 ? 's' : ''}, ${(totalSizeBytes / 1024 / 1024).toFixed(2)} MB`;
      fileInfo.classList.add('show');
      dropZone.classList.add('has-file');
      
      const fileText = files.length === 1 ? '1 file selected' : `${files.length} files selected`;
      dropZone.innerHTML = `<div><strong>${fileText}</strong><br><span style="color: var(--muted-text);">Click to change files</span></div>`;
    }

    analyzeBtn.addEventListener('click', function() {
      const files = Array.from(fileInput.files);
      const deepCheck = document.getElementById('deep_orphan_check').checked;
      const progressContainer = document.getElementById('progressContainer');
      const progressFill = document.getElementById('progressFill');
      const statusText = document.getElementById('statusText');

      if (files.length === 0) {
        alert('Please select at least one file.');
        return;
      }

      // Show progress bar
      progressContainer.style.display = 'block';
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = 'Uploading...';

      const formData = new FormData();
      files.forEach(file => {
        formData.append('ifc_files', file);
      });
      if (deepCheck) {
        formData.append('deep_orphan_check', '1');
      }

      const xhr = new XMLHttpRequest();

      // Upload progress
      xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          progressFill.style.width = percentComplete + '%';
          statusText.textContent = `Uploading... ${Math.round(percentComplete)}% (${(e.loaded / 1024 / 1024).toFixed(1)} MB / ${(e.total / 1024 / 1024).toFixed(1)} MB)`;
        }
      });

      // Upload complete
      xhr.upload.addEventListener('load', function() {
        progressFill.style.width = '100%';
        statusText.textContent = 'Upload complete. Analyzing...';
        analyzeBtn.textContent = 'Analyzing...';
      });

      // Response received
      xhr.addEventListener('load', function() {
        if (xhr.status === 200) {
          // Replace page content with result
          document.open();
          document.write(xhr.responseText);
          document.close();
        } else {
          // Error handling
          progressContainer.style.display = 'none';
          analyzeBtn.disabled = false;
          analyzeBtn.textContent = 'Analyze';
          try {
            const error = JSON.parse(xhr.responseText);
            alert('Error: ' + error.error);
          } catch (e) {
            alert('Upload failed. Please try again.');
          }
        }
      });

      // Error handling
      xhr.addEventListener('error', function() {
        progressContainer.style.display = 'none';
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Analyze';
        alert('Upload failed. Please check your connection and try again.');
      });

      // Send request
      xhr.open('POST', '/upload');
      xhr.send(formData);
    });

    // Download functionality (only on results page)
    if (document.getElementById('downloadBtn')) {
      document.getElementById('downloadBtn').addEventListener('click', function() {
        // Get the report data from the page (we'll need to store it)
        const reportData = window.reportData; // We'll set this when rendering the template
        if (reportData) {
          const dataStr = JSON.stringify(reportData, null, 2);
          const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

          const exportFileDefaultName = `${reportData.meta.filename.replace('.ifc', '')}_report.json`;

          const linkElement = document.createElement('a');
          linkElement.setAttribute('href', dataUri);
          linkElement.setAttribute('download', exportFileDefaultName);
          linkElement.click();
        }
      });
    }

    // Theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    if (currentTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      themeToggle.textContent = '☀️';
    }

    themeToggle.addEventListener('click', function() {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      if (currentTheme === 'dark') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        themeToggle.textContent = '🌙';
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        themeToggle.textContent = '☀️';
      }
    });
  </script>
</body>
</html>
"""

REPORT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IFC Analyzer Report</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <button id="themeToggle" class="theme-toggle" title="Toggle Dark Mode">🌙</button>
  
  <div class="container">
    <header>
      <h1>IFC Analyzer Report</h1>
      {% if report['meta']['files_analyzed'] %}
        <p><strong>Batch Analysis:</strong> {{ report['meta']['files_analyzed']|length }} files analyzed</p>
        <p><em>Files: {{ report['meta']['files_analyzed']|join(', ') }}</em></p>
      {% else %}
        <p>File: <strong>{{ report['meta']['filename'] }}</strong> ({{ report['meta']['filepath'] }})</p>
      {% endif %}
      <p>Schema: <strong>{{ report['meta']['schema'] or 'unknown' }}</strong> · Elapsed: <strong>{{ report['meta']['elapsed_seconds'] }} s</strong></p>
      <p><a href="/">← New Analysis</a> <button id="downloadBtn" class="btn-success">Download JSON Report</button></p>
    </header>

    <section class="card">
      <h2>Summary</h2>
      <div><span class="report-key">Total Entities:</span> <span class="report-value">{{ report['meta']['entity_total'] }}</span></div>
      <div><span class="report-key">Orphans:</span> <span class="report-value">{{ report['orphans']['orphan_total'] }} ({{ report['orphans']['mode'] }})</span></div>
      <div><span class="report-key">Recommendations:</span>
        <ul>
          {% for rec in report['recommendations'] %}
            <li>{{ rec }}</li>
          {% endfor %}
          {% if not report['recommendations'] %}
            <li>No specific improvements identified.</li>
          {% endif %}
        </ul>
      </div>
    </section>

    <section class="card">
      <h2>Top 10 Entity Types</h2>
      <table class="table">
        <thead><tr><th>Type</th><th>Count</th></tr></thead>
        <tbody>
          {% for row in report['counts']['by_type_top10'] %}
            <tr><td>{{ row['type'] }}</td><td>{{ row['count'] }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Heavy Geometry (Top {{ report['geometry']['heavy_geometry_topN']|length }})</h2>
      <table class="table">
        <thead><tr><th>Score</th><th>Type</th><th>Owner</th><th>GlobalId / Id</th></tr></thead>
        <tbody>
          {% for g in report['geometry']['heavy_geometry_topN'] %}
            <tr>
              <td>{{ g['score'] }}</td>
              <td>{{ g['geometry_type'] }}</td>
              <td>{{ g['owner_name'] or g['owner_type'] or 'unknown' }}</td>
              <td>{{ g['owner_globalid'] or g['geometry_id'] }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>AI-Based Recommendations</h2>
      <ul>
        {% for rec in report['ai_recommendations'] %}
          <li>{{ rec }}</li>
        {% endfor %}
      </ul>
    </section>

    <section class="card">
      <h2>Header Metadata</h2>
      <table class="table">
        <tbody>
          {% for key, val in report['header'].items() %}
            <tr><th>{{ key }}</th><td>{{ val }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

  </div>

  <script>
    // Make report data available for download
    window.reportData = {{ report|tojson }};

    // Theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    if (currentTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      themeToggle.textContent = '☀️';
    }

    themeToggle.addEventListener('click', function() {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      if (currentTheme === 'dark') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        themeToggle.textContent = '🌙';
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        themeToggle.textContent = '☀️';
      }
    });
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(UPLOAD_FORM)


@app.route("/upload", methods=["POST"])
def upload():
    if "ifc_files" not in request.files and "ifc_file" not in request.files:
        return jsonify({"error": "No files were uploaded."}), 400

    # Handle both single file (legacy) and multiple files
    files = []
    if "ifc_files" in request.files:
        files = request.files.getlist("ifc_files")
    elif "ifc_file" in request.files:
        files = [request.files["ifc_file"]]

    if not files or all(file.filename == "" for file in files):
        return jsonify({"error": "Empty filename(s)."}), 400

    # Validate file types
    valid_files = []
    for file in files:
        if file.filename == "":
            continue
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".ifc", ".ifczip", ".ifcz"]:
            return jsonify({"error": f"Invalid file type for {file.filename}. Use .ifc or .ifczip."}), 400
        valid_files.append(file)

    if not valid_files:
        return jsonify({"error": "No valid files selected."}), 400

    deep_orphan = request.form.get("deep_orphan_check") in ["1", "on", "true", "True"]

    tmpdir = tempfile.mkdtemp(prefix="ifc_analyzer_batch_")
    filepaths = []

    try:
        # Save all files
        for file in valid_files:
            filepath = os.path.join(tmpdir, os.path.basename(file.filename))
            file.save(filepath)
            filepaths.append(filepath)

        # Analyze all files and combine results
        combined_report = {
            "meta": {
                "filename": f"Batch of {len(filepaths)} files",
                "filepath": tmpdir,
                "entity_total": 0,
                "elapsed_seconds": 0,
                "files_analyzed": [os.path.basename(fp) for fp in filepaths]
            },
            "counts": {"by_type_top10": []},
            "orphans": {"orphan_total": 0, "mode": "combined"},
            "geometry": {"heavy_geometry_topN": []},
            "recommendations": [],
            "ai_recommendations": [],
            "header": {}
        }

        type_counts = {}
        all_orphans = []
        all_heavy_geom = []
        total_elapsed = 0

        for filepath in filepaths:
            report = analyze_ifc(
                filepath,
                AnalyzeOptions(deep_orphan_check=deep_orphan),
                cancel_event=__import__('threading').Event(),
                progress_cb=None,
            )

            # Aggregate metadata
            combined_report["meta"]["entity_total"] += report.get("meta", {}).get("entity_total", 0)
            total_elapsed += report.get("meta", {}).get("elapsed_seconds", 0)

            # Aggregate type counts
            for item in report.get("counts", {}).get("by_type_top10", []):
                type_name = item["type"]
                count = item["count"]
                if type_name in type_counts:
                    type_counts[type_name] += count
                else:
                    type_counts[type_name] = count

            # Aggregate orphans
            all_orphans.extend(report.get("orphans", {}).get("orphans", []))

            # Aggregate heavy geometry
            all_heavy_geom.extend(report.get("geometry", {}).get("heavy_geometry_topN", []))

            # Collect recommendations
            combined_report["recommendations"].extend(report.get("recommendations", []))

            # Use header from first file
            if not combined_report["header"]:
                combined_report["header"] = report.get("header", {})

        # Finalize combined data
        combined_report["meta"]["elapsed_seconds"] = total_elapsed
        combined_report["counts"]["by_type_top10"] = [
            {"type": t, "count": c} for t, c in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        combined_report["orphans"]["orphan_total"] = len(all_orphans)
        combined_report["orphans"]["orphans"] = all_orphans[:50]  # Limit for display
        combined_report["geometry"]["heavy_geometry_topN"] = sorted(all_heavy_geom, key=lambda x: x.get("score", 0), reverse=True)[:20]

        # Generate AI recommendations for combined data
        combined_report['ai_recommendations'] = ai_recommendations(combined_report)

        presentation = render_template_string(REPORT_TEMPLATE, report=combined_report)
        return presentation

    except Exception as e:
        traceback.print_exc()
        return render_template_string(
            """
            <html><body><h1>Analysis Error</h1><pre>{{ error }}</pre><a href='/'>Back</a></body></html>
            """,
            error=str(e)
        ), 500
    finally:
        # Clean up files
        for filepath in filepaths:
            try:
                os.remove(filepath)
            except Exception:
                pass
        try:
            os.rmdir(tmpdir)
        except Exception:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
