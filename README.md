
IFC Composition & Bloat Analyzer
A lightweight, Python-based GUI utility designed to audit Industry Foundation Classes (IFC) files. Unlike standard BIM viewers, this tool focuses on the "weight" of the file—analyzing whether your IFC is bloated by overly complex geometry or excessive metadata—without the overhead of 3D rendering.

🚀 Features
Geometry vs. Metadata Breakdown: Get a percentage-based breakdown of how much of your file is dedicated to 3D topology vs. property data.

Heavy Object Detection: Automatically identifies the top 5 most complex geometric objects (e.g., highly detailed furniture or mechanical equipment) and traces them back to their parent element (e.g., IfcWall, IfcFurnishingElement).

Orphan Detection: Samples the file for "orphaned" entities—data that exists in the file but is not referenced by any other element.

Header Inspection: Extracts BIM authoring information, including the originating system, schema version, and timestamp.

No 3D Required: Uses ifcopenshell for logic only, making it extremely fast even on low-spec hardware.

🛠️ Prerequisites
To run this application, you need Python 3.x and the ifcopenshell library.

Install Dependencies
Bash
pip install ifcopenshell
Note: The application includes an "Auto-Install" feature that attempts to download the library for you if it is missing.

📖 How to Use
Run the Script:

Bash
python ifc_analyzer.py
Load a File: Click the Select .IFC File button and choose your model.

View Results: The analyzer will process the file and generate a report in the output window.

Interpreting the Report
Composition Breakdown: If "Geometry" is >80%, consider simplifying 3D representations. If "Metadata" is >50%, check for duplicate property sets.

Heavy Object Report: Look for objects with high "Complexity" scores. These are often the culprits for slow model performance in Revit, ArchiCAD, or Navisworks.

Orphaned Geometry: If the tool identifies "Orphaned Geometry," these are entities that contribute to file size but don't appear in the model. These can usually be safely removed using a "Purge" command in your BIM software.

📦 Project Structure
ifc_analyzer.py: The main Python script containing the Tkinter GUI and analysis logic.

Romblad_Haxx.png: (Optional) A logo file displayed in the header. If missing, the app will run with a text-only header.

🛠️ Technical Details
The tool uses a recursive "Trace Up" logic to find geometry owners. It navigates from low-level geometry (like IfcTriangulatedFaceSet) through intermediate containers (IfcShapeRepresentation, IfcMappedItem) until it finds the high-level IfcProduct.

Categorization Keywords:
The analyzer categorizes entities based on their IFC class name:

Geometry: Points, Curves, Surfaces, Tessellations, Placements.

Metadata: Properties, Quantities, Materials, Classifications.

Relations: All IfcRel... subclasses that link data together.

⚖️ License
This project is open-source. Feel free to modify and adapt it for your BIM coordination workflows.

Disclaimer: This tool provides analysis based on entity counts and complexity scores; it does not modify your IFC files.
