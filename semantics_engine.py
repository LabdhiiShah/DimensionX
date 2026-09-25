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

import re
from collections import defaultdict
from shapely.geometry import Point, Polygon

def clean_cad_text(raw_text):
    """
    Strips MTEXT control codes, formatting tags, and extra spaces.
    """
    clean = re.sub(r'\{[^{}]*\}', '', raw_text)
    clean = re.sub(r'\\[a-zA-Z0-9]+;', '', clean)
    clean = re.sub(r'\\P', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

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
    Dynamically derives a standardized semantic type category string from input title text.
    """
    upper = title.upper()
    if "MASTER" in upper and ("BED" in upper or "BR" in upper or "RM" in upper):
        return "MASTER_BEDROOM"
    elif "BED" in upper or "BR" in upper or "SLEEP" in upper:
        return "BEDROOM"
    elif "KITCHEN" in upper or "KIT" in upper or "COOK" in upper:
        return "KITCHEN"
    elif "LIV" in upper or "DIN" in upper or "HALL" in upper or "DRAWING" in upper or "GREAT ROOM" in upper:
        return "LIVING_DINING"
    elif "MASTER" in upper and ("TOI" in upper or "BATH" in upper or "WC" in upper):
        return "MASTER_TOILET"
    elif "COMMON" in upper and ("TOI" in upper or "BATH" in upper or "WC" in upper):
        return "COMMON_TOILET"
    elif "TOI" in upper or "BATH" in upper or "WC" in upper or "RESTROOM" in upper:
        return "TOILET"
    elif "BALCONY" in upper or "VERANDAH" in upper or "TERRACE" in upper or "DECK" in upper:
        return "BALCONY"
    elif "ENTRY" in upper or "FOYER" in upper or "ENTRANCE" in upper or "PORCH" in upper:
        return "ENTRANCE"
    elif "PASSAGE" in upper or "CORRIDOR" in upper or "LOBBY" in upper or "HALLWAY" in upper:
        return "CORRIDOR"
    elif "STORE" in upper or "PANTRY" in upper or "UTILITY" in upper:
        return "UTILITY_STORE"
    else:
        # Sanitize any title to valid identifier token
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
        and associates doors to room pairs.
        """
        meaningful_rooms = room_polygons
        
        # Extract & Parse CAD Text Callouts
        parsed_callouts = []
        for l_obj in self.room_labels:
            raw_text = l_obj["text"]
            clean_text = clean_cad_text(raw_text)
            if not clean_text: continue
            
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

        # Group callouts by their semantic category (so "M. Bedroom 9'3\" x 11'0\"" and "M. BEDROOM" group together!)
        semantic_groups = defaultdict(list)
        for c in parsed_callouts:
            semantic_groups[c["semantic_category"]].append(c)

        # Ranked Candidate Assignment to ONE Room Candidate
        assigned_room_map = {} # room_id -> semantic_dict
        unmapped_labels = []

        proximity_limit = 200.0 if self.unit_to_meters <= 0.005 else (2.0 / self.unit_to_meters)
        
        for group_category, callouts in semantic_groups.items():
            best_callout = max(callouts, key=lambda c: (len(c["declared_dimensions"]), len(c["clean_title"])))
            display_title = best_callout["clean_title"]
            
            candidates = []
            for r in meaningful_rooms:
                if r["room_id"] in assigned_room_map:
                    continue
                r_poly = r["polygon"]
                c_pt = r_poly.centroid
                
                best_score = -999.0
                for c_obj in callouts:
                    pt = Point(c_obj["position"])
                    is_inside = r_poly.contains(pt)
                    dist_b = r_poly.distance(pt)
                    dist_c = pt.distance(c_pt)
                    
                    score = 0.0
                    if is_inside:
                        score += 100.0 - (dist_c * 0.01)
                    elif dist_b <= proximity_limit:
                        score += 50.0 - dist_b
                    else:
                        score = -1.0
                    if score > best_score:
                        best_score = score
                        
                if best_score > 0:
                    candidates.append((best_score, r))
                    
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            if candidates:
                best_score, best_room = candidates[0]
                assigned_room_map[best_room["room_id"]] = {
                    "name": display_title,
                    "semantic_type": group_category,
                    "declared_dimensions": best_callout["declared_dimensions"],
                    "score": round(best_score, 1),
                    "status": "CONFIRMED"
                }
            else:
                unmapped_labels.append(group_category)

        # Build Annotated Rooms List (Geometry-First!)
        annotated_rooms = []
        for r in meaningful_rooms:
            r_id = r["room_id"]
            if r_id in assigned_room_map:
                info = assigned_room_map[r_id]
                name = info["name"]
                sem_type = info["semantic_type"]
                status = info["status"]
                conf = "HIGH"
                declared_dims = info["declared_dimensions"]
            else:
                name = "UNKNOWN_SPACE"
                sem_type = "UNKNOWN_SPACE"
                status = "UNASSIGNED"
                conf = "UNASSIGNED"
                declared_dims = []

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

        print(f"[SemanticsEngine] Assigned {len(assigned_room_map)} semantic labels to existing geometry. Unmapped labels: {unmapped_labels}")
        
        # Adjacency and Connectivity
        adjacency_graph = self._build_adjacency_graph(annotated_rooms, hosted_doors)
        
        return annotated_rooms, adjacency_graph, unmapped_labels, len(meaningful_rooms), len(assigned_room_map)

    def _build_adjacency_graph(self, rooms, doors):
        adjacencies = []
        connections = []
        
        door_proximity = 100.0 if self.unit_to_meters <= 0.005 else (1.5 / self.unit_to_meters)
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
                        
                        is_connected = False
                        via_ap = None
                        for door in doors:
                            d_pt = Point(door["center"])
                            if poly_a.distance(d_pt) <= door_proximity and poly_b.distance(d_pt) <= door_proximity:
                                is_connected = True
                                via_ap = door["opening_id"]
                                break
                                
                        if is_connected:
                            connections.append({
                                "room_a": r_a["room_id"],
                                "room_b": r_b["room_id"],
                                "relationship": "CONNECTED",
                                "via_aperture": via_ap
                            })
                            
        return {
            "adjacent_pairs": adjacencies,
            "connected_pairs": connections
        }
