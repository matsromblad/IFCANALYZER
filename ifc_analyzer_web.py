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

UPLOAD_FORM = """
<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <title>IFC Analyzer Web</title>
</head>
<body>
  <h1>IFC Analyzer Web</h1>
  <p>Ladda upp en IFC-fil för analys:</p>
  <form method="post" action="/upload" enctype="multipart/form-data">
    <input type="file" name="ifc_file" accept=".ifc" required>
    <br><br>
    <label><input type="checkbox" name="deep_orphan_check" value="1"> Djup orphan-kontroll</label>
    <br>
    <button type="submit">Analysera</button>
  </form>
  <p>Resultatet returneras som JSON.</p>
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
        return jsonify(report)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
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
    app.run(host="0.0.0.0", port=5000, debug=True)
