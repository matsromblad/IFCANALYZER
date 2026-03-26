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
body {
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #f2f4f7;
    color: #1c1f23;
}
.container {
    max-width: 960px;
    margin: 30px auto;
    padding: 20px;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
header h1 {
    margin-bottom: 8px;
}
.card {
    border: 1px solid #dedeef;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 20px;
    background: #fff;
}
.btn-primary {
    background: #2f80ed;
    color: white;
    border: 0;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 16px;
    cursor: pointer;
}
.btn-primary:hover { background: #1f6ad0; }
.report-key {
    font-weight: 700;
}
.report-value {
    color: #333;
}
.table {
    width: 100%;
    border-collapse: collapse;
}
.table th,
.table td {
    border: 1px solid #e6e9ef;
    padding: 8px;
    text-align: left;
}
.table th { background: #f4f6fc; }
.progress-container {
    margin: 10px 0;
    display: none;
}
.progress-bar {
    width: 100%;
    height: 20px;
    background-color: #f0f0f0;
    border-radius: 10px;
    overflow: hidden;
}
.progress-fill {
    height: 100%;
    background-color: #2f80ed;
    width: 0%;
    transition: width 0.3s ease;
}
.status-text {
    margin-top: 5px;
    font-size: 14px;
    color: #666;
}
"""

UPLOAD_FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IFC Analyzer Web</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>IFC Analyzer Web</h1>
      <p>Upload an IFC model for analysis and get a comprehensive results page with summary.</p>
    </header>

    <section class="card">
      <div>
        <label for="ifc_file"><strong>Select IFC File</strong></label><br>
        <input type="file" id="ifc_file" name="ifc_file" accept=".ifc,.ifczip,.ifcz" required>
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
    document.getElementById('analyzeBtn').addEventListener('click', function() {
      const fileInput = document.getElementById('ifc_file');
      const deepCheck = document.getElementById('deep_orphan_check').checked;
      const progressContainer = document.getElementById('progressContainer');
      const progressFill = document.getElementById('progressFill');
      const statusText = document.getElementById('statusText');
      const analyzeBtn = document.getElementById('analyzeBtn');

      if (!fileInput.files[0]) {
        alert('Please select a file first.');
        return;
      }

      // Show progress bar
      progressContainer.style.display = 'block';
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = 'Uploading...';

      const formData = new FormData();
      formData.append('ifc_file', fileInput.files[0]);
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
  </script>
</body>
</html>
"""

REPORT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IFC Analyzer Report</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>IFC Analyzer Report</h1>
      <p>File: <strong>{{ report['meta']['filename'] }}</strong> ({{ report['meta']['filepath'] }})</p>
      <p>Schema: <strong>{{ report['meta']['schema'] or 'unknown' }}</strong> · Elapsed: <strong>{{ report['meta']['elapsed_seconds'] }} s</strong></p>
      <p><a href="/">← New Analysis</a></p>
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
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(UPLOAD_FORM)


@app.route("/upload", methods=["POST"])
def upload():
    if "ifc_file" not in request.files:
        return jsonify({"error": "No file was uploaded."}), 400

    file = request.files["ifc_file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".ifc", ".ifczip", ".ifcz"]:
        return jsonify({"error": "Invalid file type. Use .ifc or .ifczip."}), 400

    deep_orphan = request.form.get("deep_orphan_check") in ["1", "on", "true", "True"]

    tmpdir = tempfile.mkdtemp(prefix="ifc_analyzer_")
    filepath = os.path.join(tmpdir, os.path.basename(file.filename))
    file.save(filepath)

    try:
        report = analyze_ifc(
            filepath,
            AnalyzeOptions(deep_orphan_check=deep_orphan),
            cancel_event=__import__('threading').Event(),
            progress_cb=None,
        )

        report['ai_recommendations'] = ai_recommendations(report)

        presentation = render_template_string(REPORT_TEMPLATE, report=report)
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
