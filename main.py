import os
import ezdxf

from layer_detector import LayerDetector
from entity_extractor import EntityExtractor
from entity_classifier import EntityClassifier
from json_writer import JsonWriter
from visualizer import Visualizer
from wall_parser import WallParser


# ============================================================
# CONFIGURATION
# ============================================================

DXF_FILE = r"D:\end game\sample2.dxf"
OUTPUT_JSON = "converted.json"
OUTPUT_IMAGE = "wall_layout.png"


# ============================================================
# LOAD DXF
# ============================================================

print("\n==============================")
print("Loading DXF")
print("==============================")

doc = ezdxf.readfile(DXF_FILE)
print("DXF Loaded Successfully")

msp = doc.modelspace()


# ============================================================
# LAYER DETECTION
# ============================================================

print("\n==============================")
print("Layer Detection")
print("==============================")

detector = LayerDetector()
useful_layers, ignored_layers, unknown_layers = detector.detect(msp)

print("\nUseful Layers:")
print(useful_layers)

print("\nIgnored Layers:")
print(ignored_layers)

print("\nUnknown Layers:")
print(unknown_layers)


# ============================================================
# ENTITY EXTRACTION
# ============================================================

print("\n==============================")
print("Entity Extraction")
print("==============================")

extractor = EntityExtractor()
entities = extractor.extract(msp, useful_layers)

print(f"Extracted Entities : {len(entities)}")


# ============================================================
# ENTITY CLASSIFICATION
# ============================================================

print("\n==============================")
print("Entity Classification")
print("==============================")

classifier = EntityClassifier()
classified_entities = classifier.classify(entities, useful_layers)

print("\nEntity Classification Report:")
for category, items in classified_entities.items():
    print(f"{category:15} : {len(items)}")


# ============================================================
# ADVANCED WALL PARSING
# ============================================================

print("\n==============================")
print("Wall Parsing & Parallel Line Pairing")
print("==============================")

wall_parser = WallParser()
walls = wall_parser.parse(classified_entities["walls"])


# ============================================================
# PRINT FINAL LOGICAL WALLS & UNITY TRANSFORMS
# ============================================================

print("\n==============================")
print("FINAL LOGICAL WALLS (UNITY-READY)")
print("==============================")

for wall in walls:
    geometry = wall["geometry"]
    transform = wall["unity_transform"]

    wall_id = wall.get("id", "unknown")
    mode = wall.get("detection_mode", "SINGLE")
    score = wall.get("confidence_score", 0.0)

    length = geometry["length"]
    angle = geometry["angle_deg"]
    thick = wall["properties"]["thickness"]

    pos = transform["position"]
    scale = transform["scale"]

    print(
        f"{wall_id:10} | "
        f"Mode: {mode:20} | "
        f"Conf: {score:4.2f} | "
        f"Thick: {thick:4.2f}m | "
        f"Length: {length:6.2f}m | "
        f"Unity Scale Z (Thick): {scale['z']:4.2f}m"
    )

print(f"\nFinal Logical Walls : {len(walls)}")


# ============================================================
# SAVE UNITY-READY JSON
# ============================================================

print("\n==============================")
print("Saving Unity 3D JSON Output")
print("==============================")

writer = JsonWriter()
writer.save(
    filepath=OUTPUT_JSON,
    walls=walls,
    classified_entities=classified_entities,
    dxf_filename=os.path.basename(DXF_FILE),
    useful_layers=useful_layers,
    diagnostics=wall_parser.diagnostics
)


# ============================================================
# VISUALIZE LOGICAL WALLS & SAVE PLOT IMAGE
# ============================================================

print("\n==============================")
print("Visualizing Parsed Walls")
print("==============================")

visualizer = Visualizer()
visualizer.show_walls(walls, raw_wall_entities=classified_entities["walls"], save_path=OUTPUT_IMAGE, block=False)


# ============================================================
# FINAL PIPELINE REPORT
# ============================================================

print("\n==============================")
print("PIPELINE FINISHED SUCCESSFULLY")
print("==============================")

print(f"Raw Entities           : {len(entities)}")
print(f"Logical Walls          : {len(walls)}")
print(f"Paired Double-Line Walls: {wall_parser.diagnostics['paired_double_line_walls']}")
print(f"Average Confidence     : {wall_parser.diagnostics['average_confidence_score']}")
print(f"Doors                  : {len(classified_entities.get('doors', []))}")
print(f"Windows                : {len(classified_entities.get('windows', []))}")
print("==============================")