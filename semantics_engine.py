"""
Room Semantics & Adjacency Engine (Generalized Drawing-Relative Semantics)
========================================================================
Rules:
1. GEOMETRY determines WHERE a room exists.
2. TEXT determines WHAT that room is (inferred dynamically from input CAD text/mtext).
3. Synthetic rooms created from text: MUST BE 0.
4. Unlabeled room polygons are represented as UNKNOWN_SPACE.
5. Assign label to at most ONE existing meaningful room candidate polygon.
"""

import os
import re
from collections import defaultdict
from shapely.geometry import Point, Polygon

def strip_mtext_formatting(raw_text: str) -> str:
    r"""
    Remove AutoCAD MTEXT formatting codes, leaving only the human-readable text.
    Examples:
      r'\pi18.40708;{\fTrebuchet MS|b0|i0|c0|p34;dining }' -> "dining"
      r'\pi37.71182;{\fTrebuchet MS|b0|i0|c0|p34;ENTRY }' -> "ENTRY"
      r'...;Balcony\P\pi0,tz;       3\'6" x 3\'0"' -> "Balcony 3'6\" x 3'0\""
    """
    t = raw_text
    # Remove \pi...; and \pxi...; and similar stacked codes
    t = re.sub(r'\\[a-zA-Z]+[0-9.,tz;]*;', ' ', t, flags=re.IGNORECASE)
    # Remove \P (paragraph break) -> space
    t = re.sub(r'\\P', ' ', t, flags=re.IGNORECASE)
    # Remove \f, \H, \W, \C, \S, \F and their args up to ; or end
    t = re.sub(r'\\[fHWCSh][^;]*;', ' ', t, flags=re.IGNORECASE)
    # Remove remaining backslash escapes
    t = re.sub(r'\\[^a-zA-Z0-9\s]', ' ', t)
    # Remove braces
    t = t.replace('{', ' ').replace('}', ' ')
    # Collapse whitespace
    t = ' '.join(t.split())
    return t.strip()

def clean_cad_text(raw_text):
    """
    Strips MTEXT control codes, formatting tags, and extra spaces.
    """
    return strip_mtext_formatting(raw_text)

def normalize_label(text):
    """
    Case-insensitive, punctuation-tolerant label normalization.
    """
    t = text.upper()
    t = t.replace('.', ' ').replace(',', ' ').replace('/', ' ').replace('-', ' ')
    return ' '.join(t.split())

def extract_room_name_and_dimensions(clean_text):
    """
    Separates the text label (e.g. "Master Bedroom", "Kitchen", "Bed 1")
    from embedded dimension strings (e.g. "9'3\" x 11'0\"", "3.5m x 4.0m", "3500 x 2800").
    Returns (clean_title, parsed_dimensions_list).
    """
    # Imperial dimensions pattern e.g. 9'3" x 11'0"
    imp_pattern = r"(\d+)'\s*(\d+(?:\.\d+)?)\"?"
    imp_matches = re.findall(imp_pattern, clean_text)
    parsed_dims = []
    
    if imp_matches:
        for ft, inch in imp_matches:
            parsed_dims.append(float(ft) * 12.0 + float(inch))
            
    # Metric dimensions pattern e.g. 3.5 x 4.0 or 3500 x 2800
    metric_pattern = r"(\d+(?:\.\d+)?)\s*(?:m|mm)?\s*[xX*×]\s*(\d+(?:\.\d+)?)"
    metric_matches = re.findall(metric_pattern, clean_text)
    if metric_matches and not parsed_dims:
        for d1, d2 in metric_matches:
            parsed_dims.extend([float(d1), float(d2)])
            
    # Strip dimension substrings from text to isolate room title
    title = clean_text
    title = re.sub(r"\d+'\s*\d*(?:\.\d+)?\"?\s*[xX*×]?\s*\d*'?\s*\d*(?:\.\d+)?\"?", "", title)
    title = re.sub(r"\d+(?:\.\d+)?\s*(?:m|mm)?\s*[xX*×]\s*\d+(?:\.\d+)?\s*(?:m|mm)?", "", title)
    title = re.sub(r"[\(\)\[\]\{\}]", "", title)
    title = re.sub(r"^\s*[xX*×\-–:]+\s*", "", title)
    title = re.sub(r"\s*[xX*×\-–:]+\s*$", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    
    if not title:
        title = clean_text
        
    return title, parsed_dims

def derive_semantic_category(title):
    """
    Dynamically derives a standardized semantic type category string from input title text,
    handling abbreviations like 'C. Bed', 'M. Bed', 'Liv./Din.', 'C. Toi.', 'M. Toi.', etc.
    """
    upper = normalize_label(title)
    
    if any(kw in upper for kw in ["MASTER BEDROOM", "M BEDROOM", "MASTER BED", "M BED", "MBR"]):
        return "MASTER_BEDROOM"
    elif any(kw in upper for kw in ["CHILDREN BEDROOM", "C BEDROOM", "CHILD BEDROOM", "C BED", "KIDS BEDROOM"]):
        return "CHILDREN_BEDROOM"
    elif any(kw in upper for kw in ["BEDROOM", "BED ROOM", "BED", "BR", "SLEEP"]):
        return "BEDROOM"
    elif any(kw in upper for kw in ["KITCHEN", "KIT", "KITCH", "COOK"]):
        return "KITCHEN"
    elif any(kw in upper for kw in ["LIVING DINING", "LIV DIN", "LTR DIN", "LIVING", "LIV", "DINING", "DIN", "LTR", "HALL", "DRAWING", "GREAT ROOM"]):
        return "LIVING_DINING"
    elif any(kw in upper for kw in ["MASTER TOILET", "M TOILET", "M TOI", "MASTER BATH", "M BATH", "M WC"]):
        return "MASTER_TOILET"
    elif any(kw in upper for kw in ["COMMON TOILET", "C TOILET", "C TOI", "CHILD TOILET", "COMMON BATH", "C BATH", "C WC"]):
        return "COMMON_TOILET"
    elif any(kw in upper for kw in ["TOILET", "TOI", "BATHROOM", "BATH", "WC", "RESTROOM"]):
        return "BATHROOM"
    elif any(kw in upper for kw in ["BALCONY", "BALC", "BAL", "VERANDAH", "TERRACE", "DECK"]):
        return "BALCONY"
    elif any(kw in upper for kw in ["ENTRY", "FOYER", "ENTRANCE", "PORCH"]):
        return "ENTRANCE"
    elif any(kw in upper for kw in ["PASSAGE", "PASS", "CORRIDOR", "LOBBY", "HALLWAY"]):
        return "CORRIDOR"
    elif any(kw in upper for kw in ["STORAGE", "STORE", "STO", "PANTRY", "UTILITY", "UTIL"]):
        return "UTILITY_STORE"
    elif any(kw in upper for kw in ["SITE", "PLOT", "BOUNDARY"]):
        return "SITE"
    else:
        sanitized = re.sub(r'[^A-Z0-9_]', '_', upper).strip('_')
        return sanitized if sanitized else "UNKNOWN_SPACE"

class SemanticsEngine:
    def __init__(self, room_label_candidates, unit_to_meters=1.0):
        self.room_labels = room_label_candidates
        self.unit_to_meters = unit_to_meters

    def process_room_semantics(self, room_polygons, hosted_doors):
        """
        Classifies room candidates, extracts CAD text callouts dynamically,
        performs ranked semantic label assignment to existing geometry only,
        and applies geometric fallback for unlabeled rooms.
        """
        meaningful_rooms = room_polygons
        
        # 1. Extract & Parse CAD Text Callouts
        parsed_callouts = []
        for l_obj in self.room_labels:
            raw_text = l_obj["text"]
            clean_text = clean_cad_text(raw_text)
            if not clean_text:
                continue
            
            title, dims = extract_room_name_and_dimensions(clean_text)
            sem_category = derive_semantic_category(title)
            
            parsed_callouts.append({
                "raw_text": raw_text,
                "clean_title": title,
                "semantic_category": sem_category,
                "position": l_obj["position"],
                "declared_dimensions": dims,
                "layer": l_obj["layer"]
            })

        assigned_room_map = {} # room_id -> semantic_dict
        unmapped_labels = []

        # 2. Text-to-Room Spatial Matching
        used_rooms = set()
        used_callouts = set()
        
        proximity_limit = 200.0 if self.unit_to_meters <= 0.005 else (2.0 / self.unit_to_meters)
        
        matches = []
        for c_idx, c_obj in enumerate(parsed_callouts):
            pt = Point(c_obj["position"])
            for r in meaningful_rooms:
                r_id = r["room_id"]
                r_poly = r["polygon"]
                c_pt = r_poly.centroid
                
                min_x, min_y, max_x, max_y = r_poly.bounds
                w, h = max_x - min_x, max_y - min_y
                max_dim = max(w, h, 1e-3)
                
                is_inside = r_poly.contains(pt)
                dist_b = r_poly.distance(pt)
                dist_c = pt.distance(c_pt)
                
                score = -1.0
                if is_inside:
                    score = 1000.0 - dist_c * 0.01
                elif dist_b <= max(1.5 * max_dim, proximity_limit):
                    score = 500.0 - dist_b
                    
                if score > 0:
                    matches.append((score, c_idx, r_id))
                    
        # Sort matches by highest score (inside centroid > close boundary)
        matches.sort(key=lambda x: x[0], reverse=True)
        
        for score, c_idx, r_id in matches:
            if c_idx in used_callouts or r_id in used_rooms:
                continue
            c_obj = parsed_callouts[c_idx]
            
            assigned_room_map[r_id] = {
                "name": c_obj["clean_title"],
                "semantic_type": c_obj["semantic_category"],
                "declared_dimensions": c_obj["declared_dimensions"],
                "score": round(score, 1),
                "status": "CONFIRMED",
                "source": "text",
                "confidence": "HIGH"
            }
            used_rooms.add(r_id)
            used_callouts.add(c_idx)

        for c_idx, c_obj in enumerate(parsed_callouts):
            if c_idx not in used_callouts:
                unmapped_labels.append(c_obj["semantic_category"])

        # 3. Geometric Fallback for Unlabeled Rooms
        max_area = max((r["polygon"].area for r in meaningful_rooms), default=0) if meaningful_rooms else 0
        
        for r in meaningful_rooms:
            r_id = r["room_id"]
            if r_id in used_rooms:
                continue
                
            r_poly = r["polygon"]
            area_m2 = r_poly.area * (self.unit_to_meters ** 2) if self.unit_to_meters > 0 else r_poly.area
            
            inferred_label = None
            inferred_cat = None
            
            # Tiny rooms (< 4.0 m²) tend to be bathrooms
            if area_m2 < 4.0 and len(meaningful_rooms) > 1:
                inferred_label = "Bathroom"
                inferred_cat = "BATHROOM"
            # Largest room in drawing is usually Living / Dining
            elif abs(r_poly.area - max_area) < 1e-3 and max_area > 0:
                inferred_label = "Living/Dining"
                inferred_cat = "LIVING_DINING"
            # Medium/large rooms (>= 4.0 m²) default to Bedroom
            elif area_m2 >= 4.0:
                inferred_label = "Bedroom"
                inferred_cat = "BEDROOM"
            else:
                inferred_label = "UNKNOWN_SPACE"
                inferred_cat = "UNKNOWN_SPACE"

            if inferred_cat != "UNKNOWN_SPACE":
                assigned_room_map[r_id] = {
                    "name": inferred_label,
                    "semantic_type": inferred_cat,
                    "declared_dimensions": [],
                    "score": 50.0,
                    "status": "INFERRED",
                    "source": "geometry",
                    "confidence": "MEDIUM"
                }

        # 4. Build Annotated Rooms List & Log Decisions
        annotated_rooms = []
        for r in meaningful_rooms:
            r_id = r["room_id"]
            if r_id in assigned_room_map:
                info = assigned_room_map[r_id]
                name = info["name"]
                sem_type = info["semantic_type"]
                status = info["status"]
                conf = info.get("confidence", "HIGH")
                declared_dims = info["declared_dimensions"]
                source = info.get("source", "text")
            else:
                name = "UNKNOWN_SPACE"
                sem_type = "UNKNOWN_SPACE"
                status = "UNASSIGNED"
                conf = "UNASSIGNED"
                declared_dims = []
                source = "default"

            print(f"[SemanticsEngine] {r_id}: label={name} source={source} conf={conf}")

            annotated_rooms.append({
                "room_id": r_id,
                "name": name,
                "semantic_type": sem_type,
                "status": status,
                "confidence": conf,
                "area_sq_units": r["area"],
                "perimeter_units": r["perimeter"],
                "parsed_dimensions": declared_dims,
                "declared_dimensions": declared_dims,
                "polygon": r["polygon"],
                "bounds": r["bounds"]
            })

        num_semantic = sum(1 for room in annotated_rooms if room["semantic_type"] != "UNKNOWN_SPACE")
        print(f"[SemanticsEngine] Assigned {num_semantic} semantic labels to existing geometry. Unmapped labels: {unmapped_labels}")
        
        # Adjacency and Connectivity
        adjacency_graph = self._build_adjacency_graph(annotated_rooms, hosted_doors)
        
        return annotated_rooms, adjacency_graph, unmapped_labels, len(meaningful_rooms), num_semantic

    def _build_adjacency_graph(self, rooms, doors):
        adjacencies = []
        
        min_shared_len = 1.0 if self.unit_to_meters <= 0.005 else max(0.1 / self.unit_to_meters, 0.5)
        
        for i in range(len(rooms)):
            r_a = rooms[i]
            poly_a = r_a["polygon"]
            for j in range(i + 1, len(rooms)):
                r_b = rooms[j]
                poly_b = r_b["polygon"]
                
                if poly_a.intersects(poly_b):
                    inter = poly_a.intersection(poly_b)
                    if inter.length >= min_shared_len:
                        adjacencies.append({
                            "room_a": r_a["room_id"],
                            "room_b": r_b["room_id"],
                            "relationship": "ADJACENT",
                            "shared_length": round(inter.length, 2)
                        })

        connected_pairs = []
        for door in doors:
            connects = door.get("connects", [])
            if len(connects) >= 2:
                for i in range(len(connects)):
                    for j in range(i + 1, len(connects)):
                        a, b = connects[i], connects[j]
                        if a == "EXTERIOR" or b == "EXTERIOR":
                            continue
                        connected_pairs.append({
                            "room_a": a,
                            "room_b": b,
                            "relationship": "connected",
                            "via_aperture": door.get("opening_id", "")
                        })

        return {
            "adjacent_pairs": adjacencies,
            "connected_pairs": connected_pairs
        }
