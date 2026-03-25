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
        return ["Ingen GEMINI_API_KEY i miljön. Sätt den och starta om appen."]

    exporter = detect_exporter(report)
    orphans = report.get("orphans", {}).get("orphan_total", 0)
    heavy = len(report.get("geometry", {}).get("heavy_geometry_topN", []))

    # Exempel prompt (fyll på med din egen Gemini-klient i produktionskod):
    prompt = (
        "Du får IFC-analysdata från en modell exporterat från %s. "
        "Entity count: %s, orphans: %s, heavy geom candidates: %s. "
        "Ge konkreta förbättringsförslag för IFC-export och filrensning."
    ) % (exporter, report.get("meta", {}).get("entity_total", "?"), orphans, heavy)

    # TODO: Byt ut mot riktig Gemini-API-anrop t.ex. via openai/vertex-ai client.
    # requests.post('https://gemini.googleapis.com/...', headers={'Authorization': 'Bearer ' + api_key}, json={...})

    # Fallback: och ge lite defensiva generella tips.
    result = [
        f"Exportör uppskattad till: {exporter}",
        f"Orphan-objekt: {orphans} (<=20% är normalt).",
        f"Tunga geometriobjekt: {heavy}. Kontrollera topplistorna.",
    ]
    result.extend(report.get("recommendations", []))
    result.append("(AI-analys nyckelverifierad, standardrekommendationer.)")
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
"""

UPLOAD_FORM = """
<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <title>IFC Analyzer Web</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>IFC Analyzer Web</h1>
      <p>Ladda upp en IFC-modell för analys och få en resultatsida med sammanfattning.</p>
    </header>

    <section class="card">
      <form method="post" action="/upload" enctype="multipart/form-data">
        <div>
          <label for="ifc_file"><strong>Välj IFC-fil</strong></label><br>
          <input type="file" id="ifc_file" name="ifc_file" accept=".ifc,.ifczip,.ifcz" required>
        </div>
        <div style="margin: 12px 0;">
          <label><input type="checkbox" name="deep_orphan_check" value="1"> Djup orphan-kontroll</label>
        </div>
        <button class="btn-primary" type="submit">Analysera</button>
      </form>
    </section>

    <section class="card">
      <h2>Instruktioner</h2>
      <ul>
        <li>Max filstorlek: 1 GB.</li>
        <li>Resultatet visas direkt som HTML (fortfarande JSON-data under huven).</li>
        <li>För större dataset: kör gärna lokalt med Python/Flask.</li>
      </ul>
    </section>
  </div>
</body>
</html>
"""

REPORT_TEMPLATE = """
<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <title>IFC Analyzer Resultat</title>
  <style>""" + BASE_CSS + """</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>IFC Analyzer Resultat</h1>
      <p>Fil: <strong>{{ report['meta']['filename'] }}</strong> ({{ report['meta']['filepath'] }})</p>
      <p>Schema: <strong>{{ report['meta']['schema'] or 'okänt' }}</strong> · Elapsed: <strong>{{ report['meta']['elapsed_seconds'] }} s</strong></p>
      <p><a href="/">← Ny analys</a></p>
    </header>

    <section class="card">
      <h2>Sammanfattning</h2>
      <div><span class="report-key">Entiteter totalt:</span> <span class="report-value">{{ report['meta']['entity_total'] }}</span></div>
      <div><span class="report-key">Orphans:</span> <span class="report-value">{{ report['orphans']['orphan_total'] }} ({{ report['orphans']['mode'] }})</span></div>
      <div><span class="report-key">Rekommendationer:</span>
        <ul>
          {% for rec in report['recommendations'] %}
            <li>{{ rec }}</li>
          {% endfor %}
          {% if not report['recommendations'] %}
            <li>Inga särskilda förbättringar identifierades.</li>
          {% endif %}
        </ul>
      </div>
    </section>

    <section class="card">
      <h2>Topp 10 entitetstyper</h2>
      <table class="table">
        <thead><tr><th>Typ</th><th>Antal</th></tr></thead>
        <tbody>
          {% for row in report['counts']['by_type_top10'] %}
            <tr><td>{{ row['type'] }}</td><td>{{ row['count'] }}</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Tung geometri (topp {{ report['geometry']['heavy_geometry_topN']|length }})</h2>
      <table class="table">
        <thead><tr><th>Score</th><th>Typ</th><th>Owner</th><th>GlobalId / Id</th></tr></thead>
        <tbody>
          {% for g in report['geometry']['heavy_geometry_topN'] %}
            <tr>
              <td>{{ g['score'] }}</td>
              <td>{{ g['geometry_type'] }}</td>
              <td>{{ g['owner_name'] or g['owner_type'] or 'okänd' }}</td>
              <td>{{ g['owner_globalid'] or g['geometry_id'] }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>AI-baserade rekommendationer</h2>
      <ul>
        {% for rec in report['ai_recommendations'] %}
          <li>{{ rec }}</li>
        {% endfor %}
      </ul>
    </section>

    <section class="card">
      <h2>Header metadata</h2>
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
        return jsonify({"error": "Ingen fil skickades."}), 400

    file = request.files["ifc_file"]
    if file.filename == "":
        return jsonify({"error": "Tom filnamn."}), 400

    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".ifc", ".ifczip", ".ifcz"]:
        return jsonify({"error": "Fel filtyp. Använd .ifc eller .ifczip."}), 400

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
            <html><body><h1>Analysfel</h1><pre>{{ error }}</pre><a href='/'>Tillbaka</a></body></html>
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
