import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import os
import threading
import collections
import time
import sys
import subprocess

# --- Safe Import for ifcopenshell ---
IFC_AVAILABLE = False
try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

class IfcAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IFC Bloat Analyzer")
        self.root.geometry("900x700")
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", font=("Helvetica", 10))

        # --- Header Section ---
        header_frame = tk.Frame(root, bg="#f0f0f0", pady=10)
        header_frame.pack(fill="x")

        # 1. Text Section (Left)
        text_frame = tk.Frame(header_frame, bg="#f0f0f0")
        text_frame.pack(side="left", padx=20, fill="y")
        
        lbl_title = tk.Label(text_frame, text="IFC Composition & Bloat Analyzer", 
                             font=("Helvetica", 16, "bold"), bg="#f0f0f0", fg="#333")
        lbl_title.pack(anchor="w")
        
        lbl_subtitle = tk.Label(text_frame, text="Analyze geometry vs. metadata weight without 3D rendering", 
                                font=("Helvetica", 10), bg="#f0f0f0", fg="#666")
        lbl_subtitle.pack(anchor="w")

        # 2. Image Section (Right)
        # Try to locate the image in the current directory or script directory
        self.logo_image = None
        img_filename = "Romblad_Haxx.png"
        
        # Robust path finding (handles script run vs compiled exe)
        if getattr(sys, 'frozen', False):
            # If running as compiled exe, look in the same folder as the exe
            base_path = os.path.dirname(sys.executable)
        else:
            # If running as script, look in script directory
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        img_path = os.path.join(base_path, img_filename)

        # Fallback: check current working directory if not found in base path
        if not os.path.exists(img_path):
            img_path = img_filename

        if os.path.exists(img_path):
            try:
                # Load image
                raw_img = tk.PhotoImage(file=img_path)
                
                # Simple auto-scaling: If image is wider than 200px, subsample it down
                # (Tkinter PhotoImage subsample is integer only, but works for basic scaling)
                if raw_img.width() > 200:
                    scale_factor = int(raw_img.width() / 200)
                    if scale_factor > 1:
                        self.logo_image = raw_img.subsample(scale_factor, scale_factor)
                    else:
                        self.logo_image = raw_img
                else:
                    self.logo_image = raw_img
                
                # Display Image
                lbl_logo = tk.Label(header_frame, image=self.logo_image, bg="#f0f0f0")
                lbl_logo.pack(side="right", padx=20)
                
            except Exception as e:
                # Fail silently but print to console, app continues working
                print(f"Warning: Could not load logo image. {e}")

        # --- Control Section ---
        control_frame = tk.Frame(root, pady=10)
        control_frame.pack(fill="x", padx=20)
        
        self.btn_load = ttk.Button(control_frame, text="Select .IFC File", command=self.select_file)
        self.btn_load.pack(side="left", padx=5)
        
        self.lbl_status = ttk.Label(control_frame, text="Ready", foreground="blue")
        self.lbl_status.pack(side="left", padx=10)

        self.progress = ttk.Progressbar(control_frame, orient="horizontal", length=200, mode="indeterminate")
        
        # --- Output Section ---
        self.txt_output = scrolledtext.ScrolledText(root, font=("Consolas", 10), state="disabled")
        self.txt_output.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Store analysis results
        self.filepath = None

        # --- Check Dependency on Startup ---
        if not IFC_AVAILABLE:
            self.show_missing_dependency_ui()

    def show_missing_dependency_ui(self):
        """Disables normal usage and shows installation help if library is missing."""
        self.btn_load.config(state="disabled")
        self.lbl_status.config(text="MISSING LIBRARY", foreground="red")
        
        # Check if running as compiled executable (Frozen)
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            msg = (
                "CRITICAL ERROR: The 'ifcopenshell' library is missing from this executable.\n\n"
                "The application was not packaged correctly.\n"
                "Please rebuild using: --collect-all ifcopenshell"
            )
            self.log(msg)
        else:
            msg = (
                "CRITICAL ERROR: The 'ifcopenshell' library is not found.\n\n"
                "This application cannot work without it.\n\n"
                "To fix this, open your terminal/command prompt and run:\n"
                "   python -m pip install ifcopenshell\n\n"
                "Attempting to auto-install now? (Check console for details)"
            )
            self.log(msg)
            
            # Add a button to try auto-installing
            self.btn_install = ttk.Button(self.root, text="Attempt Auto-Install", command=self.attempt_auto_install)
            self.btn_install.pack(pady=10)

    def attempt_auto_install(self):
        """Tries to install the package using subprocess."""
        self.log("\nRunning installation command...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ifcopenshell"])
            self.log("\nSUCCESS: Library installed. Please restart this application.")
            messagebox.showinfo("Success", "Library installed successfully!\nPlease close and restart the app.")
        except subprocess.CalledProcessError as e:
            self.log(f"\nFAILURE: Installation failed. Error code: {e.returncode}")
            self.log("Please copy/paste this command into your terminal manually:")
            self.log(f"{sys.executable} -m pip install ifcopenshell")
        except Exception as e:
            self.log(f"\nERROR: {e}")

    def select_file(self):
        if not IFC_AVAILABLE:
            messagebox.showerror("Error", "Library missing. Please install ifcopenshell first.")
            return

        filetypes = (("IFC Files", "*.ifc"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(title="Open IFC File", initialdir=os.getcwd(), filetypes=filetypes)
        if filename:
            self.filepath = filename
            self.lbl_status.config(text=f"Selected: {os.path.basename(filename)}")
            self.start_analysis()

    def start_analysis(self):
        self.btn_load.config(state="disabled")
        self.progress.pack(side="right", padx=5)
        self.progress.start(10)
        self.txt_output.config(state="normal")
        self.txt_output.delete(1.0, tk.END)
        self.txt_output.insert(tk.END, "Loading and parsing file... This may take a moment for large files.\n")
        self.txt_output.config(state="disabled")
        
        thread = threading.Thread(target=self.run_analysis_logic)
        thread.daemon = True
        thread.start()

    def log(self, message):
        """Thread-safe logging to text area"""
        def _write():
            self.txt_output.config(state="normal")
            self.txt_output.insert(tk.END, message + "\n")
            self.txt_output.see(tk.END)
            self.txt_output.config(state="disabled")
        self.root.after(0, _write)

    # --- New Logic: Find what owns the heavy geometry ---
    def find_owner_of_geometry(self, geo_entity, ifc_file):
        """
        Traces back from a geometry item (e.g. IfcTriangulatedFaceSet)
        to the IfcProduct (e.g. IfcDoor, IfcWall) that uses it.
        Improved to handle nested geometry containers.
        """
        # Limit recursion depth to prevent infinite loops in circular refs
        max_depth = 12
        
        def trace_up(entity, depth):
            if depth > max_depth: return None
            
            # Use get_inverse to find what references this entity
            try:
                refs = ifc_file.get_inverse(entity)
            except:
                return None

            for ref in refs:
                # 1. Found the owner (Product)
                if ref.is_a("IfcProduct"):
                    return ref
                elif ref.is_a("IfcTypeProduct"):
                    return ref # It belongs to a type definition (e.g. Door Style)
                
                # 2. Intermediate Nodes - keep climbing
                elif ref.is_a("IfcProductDefinitionShape"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                elif ref.is_a("IfcShapeRepresentation"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                elif ref.is_a("IfcRepresentationMap"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                elif ref.is_a("IfcMappedItem"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                elif ref.is_a("IfcStyledItem"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                
                # 3. Intermediate Geometry Containers (The Fix)
                # IfcClosedShell is used by IfcFacetedBrep, which is an IfcRepresentationItem.
                # IfcRepresentationItem is the catch-all for intermediate geometry.
                elif ref.is_a("IfcRepresentationItem"):
                    result = trace_up(ref, depth + 1)
                    if result: return result
                    
            return None

        return trace_up(geo_entity, 0)

    def run_analysis_logic(self):
        start_time = time.time()
        try:
            # 1. Load File
            ifc_file = ifcopenshell.open(self.filepath)
            
            self.log("-" * 60)
            self.log(f"FILE: {os.path.basename(self.filepath)}")

            # 2. Robust Header Parsing
            header_info = {}
            try:
                # Get the header object
                # Some versions use ifc_file.header, others wrapped_data.header
                header = getattr(ifc_file, "header", None)
                if not header and hasattr(ifc_file, "wrapped_data"):
                    header = getattr(ifc_file.wrapped_data, "header", None)

                # Schema is usually safe on the file object itself
                header_info["SCHEMA"] = ifc_file.schema

                if header:
                    # Parse FILE_NAME
                    if hasattr(header, "file_name"):
                        fn = header.file_name
                        if hasattr(fn, "name"): header_info["NAME"] = fn.name
                        if hasattr(fn, "time_stamp"): header_info["TIMESTAMP"] = fn.time_stamp
                        if hasattr(fn, "author"): header_info["AUTHOR"] = fn.author
                        if hasattr(fn, "organization"): header_info["ORGANIZATION"] = fn.organization
                        if hasattr(fn, "preprocessor_version"): header_info["PREPROCESSOR"] = fn.preprocessor_version
                        if hasattr(fn, "originating_system"): header_info["ORIGINATING SYSTEM"] = fn.originating_system
                        if hasattr(fn, "authorization"): header_info["AUTHORIZATION"] = fn.authorization

                    # Parse FILE_DESCRIPTION
                    if hasattr(header, "file_description"):
                        fd = header.file_description
                        if hasattr(fd, "description"): header_info["DESCRIPTION"] = fd.description
                        if hasattr(fd, "implementation_level"): header_info["IMPLEMENTATION LEVEL"] = fd.implementation_level

            except Exception as e:
                self.log(f"Warning: Partial header parse failure ({str(e)})")

            # Print Header Info
            for key, val in header_info.items():
                if val: # Only print if has value
                    # Clean up lists (often tuples in ifcopenshell)
                    val_str = str(val)
                    if isinstance(val, (list, tuple)):
                        if len(val) == 1:
                            val_str = str(val[0])
                        else:
                            val_str = ", ".join(str(v) for v in val)
                    self.log(f"{key}: {val_str}")
            
            self.log("-" * 60)

            # 3. Categorization & Counting
            cat_geometry = 0
            cat_metadata = 0
            cat_relations = 0
            cat_structure = 0
            
            entity_counts = collections.Counter()
            
            geo_keywords = [
                "POINT", "CURVE", "SURFACE", "FACE", "LOOP", "VERTEX", "EDGE", 
                "SOLID", "SHAPE", "REPRESENTATION", "GEOMETRIC", "PLACEMENT", 
                "TRANSFORMATION", "VECTOR", "DIRECTION", "AXIS", "CARTESIAN", 
                "TESSELLATED", "POLY", "INDEXED"
            ]
            
            meta_keywords = [
                "PROPERTY", "QUANTITY", "OWNER", "APPLICATION", "ORGANIZATION", 
                "PERSON", "MEASURE", "UNIT", "DIMENSIONAL", "CLASSIFICATION", 
                "MATERIAL", "STYLE", "PRESENTATION", "COLOR", "PATTERN", "FONT"
            ]

            # Compatible iteration
            try:
                all_entities = list(ifc_file)
            except Exception as e:
                self.log(f"Warning: Direct iteration failed ({str(e)}). Trying fallback...")
                all_entities = []
                for t in ["IfcProduct", "IfcRelationship", "IfcPropertyDefinition", "IfcRepresentationItem"]:
                    try:
                        all_entities.extend(ifc_file.by_type(t))
                    except: pass
            
            cat_total = len(all_entities)

            # --- Heavy Object Detection Arrays ---
            heavy_geoms = [] # List of tuples: (score, entity, type_name)

            orphans_found = 0
            check_orphans_limit = 1000 
            
            self.log("\nScanning entities...")

            for i, entity in enumerate(all_entities):
                e_type = entity.is_a().upper()
                entity_counts[e_type] += 1
                
                # Categorization
                if e_type.startswith("IFCREL"):
                    cat_relations += 1
                elif any(k in e_type for k in geo_keywords):
                    cat_geometry += 1
                elif any(k in e_type for k in meta_keywords):
                    cat_metadata += 1
                else:
                    cat_structure += 1

                # --- SMART GEOMETRY DENSITY CHECK ---
                # We assign a 'score' based on polygon/vertex count
                score = 0
                if entity.is_a("IfcTriangulatedFaceSet"):
                    # IFC4 Mesh: Count the triangles in CoordIndex
                    try:
                        # CoordIndex is a list of lists/tuples, or flattened list
                        score = len(entity.CoordIndex)
                    except: pass
                elif entity.is_a("IfcConnectedFaceSet"):
                    # IFC2x3/4 B-Rep: Count the faces
                    try:
                        score = len(entity.CfsFaces)
                    except: pass
                elif entity.is_a("IfcPolyLoop"):
                    # High vertex count polygon
                    try:
                        score = len(entity.Polygon)
                    except: pass
                
                # If it's significant, store it for later ownership analysis
                # Thresholds: >100 faces/points usually means detailed geom
                if score > 100:
                    heavy_geoms.append((score, entity, e_type))

                # Orphan check
                if i < check_orphans_limit and e_type != "IFCPROJECT":
                    try:
                        refs = ifc_file.get_inverse(entity)
                        if len(refs) == 0:
                            orphans_found += 1
                    except:
                        pass

            # 4. Generate Report
            pc_geo = (cat_geometry / cat_total) * 100 if cat_total > 0 else 0
            pc_meta = (cat_metadata / cat_total) * 100 if cat_total > 0 else 0
            pc_rel = (cat_relations / cat_total) * 100 if cat_total > 0 else 0
            pc_struct = (cat_structure / cat_total) * 100 if cat_total > 0 else 0

            self.log(f"\nTOTAL ENTITIES: {cat_total:,}")
            self.log("\n--- COMPOSITION BREAKDOWN (Entity Count) ---")
            self.log(f"1. GEOMETRY/TOPOLOGY: {cat_geometry:,} ({pc_geo:.2f}%)")
            self.log(f"2. METADATA/PROPERTIES: {cat_metadata:,} ({pc_meta:.2f}%)")
            self.log(f"3. STRUCTURE/RELATION: {cat_relations:,} ({pc_rel:.2f}%)")
            self.log(f"4. CORE/DEFINITIONS: {cat_structure:,} ({pc_struct:.2f}%)")
            
            # --- HEAVY OBJECT REPORT ---
            self.log("\n--- HEAVY OBJECT DETECTION (Top 5 Geometric Densities) ---")
            self.log("Identifying objects with high polygon/face counts (e.g., 3D furniture, detailed hardware)...")
            
            if not heavy_geoms:
                self.log("  No significantly heavy single geometry chunks found (Threshold > 100 faces/points).")
            else:
                # Sort by score descending
                heavy_geoms.sort(key=lambda x: x[0], reverse=True)
                top_heavy = heavy_geoms[:5] # Top 5
                
                for idx, (score, geom_entity, g_type) in enumerate(top_heavy):
                    # Find who owns this geometry
                    owner = self.find_owner_of_geometry(geom_entity, ifc_file)
                    
                    if owner:
                        owner_type = owner.is_a()
                        owner_id = f"#{owner.id()}"
                        # Try to get Name, or GlobalId
                        try: owner_name = getattr(owner, "Name", "Unnamed")
                        except: owner_name = "Unnamed"
                        
                        if not owner_name: 
                            try: owner_name = f"GlobalId: {owner.GlobalId}"
                            except: owner_name = "No Identifier"

                        self.log(f"\n  {idx+1}. {owner_type} [{owner_id}]")
                        self.log(f"     Name: {owner_name}")
                        self.log(f"     Complexity: {score} elements ({g_type})")
                    else:
                        # Explicitly label as orphan
                        self.log(f"\n  {idx+1}. ORPHANED GEOMETRY (No Owner Found)")
                        self.log(f"     ID: #{geom_entity.id()}")
                        self.log(f"     Complexity: {score} elements ({g_type})")
                        self.log("     Action: This geometry is likely unused. Run 'Purge' in your BIM tool.")

            self.log("\n--- BLOAT ANALYSIS ---")
            top_5 = entity_counts.most_common(5)
            self.log("TOP 5 MOST COMMON ENTITIES (Frequency):")
            for i, (name, count) in enumerate(top_5):
                self.log(f"  {i+1}. {name}: {count:,}")

            if "IfcOwnerHistory" in entity_counts and entity_counts["IfcOwnerHistory"] > 1:
                oh_count = entity_counts["IfcOwnerHistory"]
                self.log(f"\nWARNING: Found {oh_count} IfcOwnerHistory entities.")

            if cat_total > 0:
                self.log(f"\nORPHAN CHECK (Sampled first {check_orphans_limit:,} entities):")
                if orphans_found > 0:
                    self.log(f"  - Estimated {orphans_found} potentially unreferenced entities in sample.")
                else:
                    self.log("  - No obvious orphaned data found in sample.")

            duration = time.time() - start_time
            self.log(f"\nAnalysis complete in {duration:.2f} seconds.")

        except Exception as e:
            self.log(f"\nERROR: Failed to process file.\n{str(e)}")
            messagebox.showerror("Error", f"Failed to analyze file:\n{str(e)}")
        finally:
            self.root.after(0, self.stop_progress)

    def stop_progress(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.btn_load.config(state="normal")
        self.lbl_status.config(text="Done")

if __name__ == "__main__":
    root = tk.Tk()
    app = IfcAnalyzerApp(root)
    root.mainloop()
