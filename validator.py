"""
House2D Architectural Validation Suite (Generalized Drawing-Relative Validation)
==================================================================================
Validates House2D model for structural coherence, zero synthetic room geometry,
drawing-relative room semantics, door-to-room connectivity, and scale.
Describes WHY a result is uncertain rather than forcing an expected structure.
"""

import json

class House2DValidator:
    def __init__(self, house2d_data):
        self.data = house2d_data
        self.blocking_errors = []
        self.warnings = []

    def validate(self):
        print("[House2DValidator] Running drawing-relative architectural validation...")
        
        self._validate_units_and_scale()
        self._validate_geometry_and_topology()
        self._validate_room_coherence_and_semantics()
        self._validate_apertures()
        self._validate_footprint()

        is_valid = len(self.blocking_errors) == 0
        
        report = {
            "validation_passed": is_valid,
            "blocking_error_count": len(self.blocking_errors),
            "warning_count": len(self.warnings),
            "blocking_errors": self.blocking_errors,
            "warnings": self.warnings
        }
        
        print(f"[House2DValidator] Result: {'PASSED' if is_valid else 'FAILED / NEEDS_REVIEW'} ({len(self.blocking_errors)} blocking errors, {len(self.warnings)} warnings).")
        return report

    def _validate_units_and_scale(self):
        units = self.data.get("units", {})
        scale_to_m = units.get("scale_to_meters", 1.0)
        confidence = units.get("scale_confidence", "LOW")
        
        if scale_to_m <= 0 or scale_to_m > 1000.0:
            self.blocking_errors.append({
                "category": "UNITS",
                "code": "IMPLAUSIBLE_SCALE_FACTOR",
                "message": f"Scale to meters factor {scale_to_m} is out of realistic architectural range."
            })
        if confidence == "LOW":
            self.warnings.append({
                "category": "UNITS",
                "code": "LOW_SCALE_CONFIDENCE",
                "message": "Scale determination has low confidence based on input DXF evidence. Manual verification recommended."
            })

    def _validate_geometry_and_topology(self):
        walls = self.data["building_components"].get("walls", [])
        if not walls:
            self.blocking_errors.append({
                "category": "GEOMETRY",
                "code": "NO_WALLS_FOUND",
                "message": "No wall components exist in House2D."
            })
            return
            
        wall_ids = set()
        for w in walls:
            wid = w["wall_id"]
            if wid in wall_ids:
                self.blocking_errors.append({
                    "category": "TOPOLOGY",
                    "code": "DUPLICATE_WALL_ID",
                    "message": f"Duplicate wall ID '{wid}' found in topological wall graph."
                })
            wall_ids.add(wid)

    def _validate_room_coherence_and_semantics(self):
        rooms = self.data["building_components"].get("rooms", [])
        if not rooms:
            self.blocking_errors.append({
                "category": "ROOMS",
                "code": "NO_ROOMS_RECONSTRUCTED",
                "message": "No room polygons were extracted from planar graph."
            })
            return

        # Check for synthetic rooms created from text
        for r in rooms:
            if r.get("source_derivation") == "SYNTHETIC_TEXT_RECTANGLE":
                self.blocking_errors.append({
                    "category": "SEMANTICS",
                    "code": "SYNTHETIC_ROOM_CREATED_FROM_TEXT",
                    "message": f"Room '{r['room_id']}' was generated synthetically from text without underlying geometry."
                })

        # Check duplicate specific room text label assignments
        title_counts = {}
        for r in rooms:
            name = r["name"]
            if name not in ("UNKNOWN_SPACE", "UNASSIGNED"):
                title_counts[name] = title_counts.get(name, 0) + 1

        for name, count in title_counts.items():
            if count > 1:
                self.warnings.append({
                    "category": "SEMANTICS",
                    "code": "DUPLICATE_EXPLICIT_ROOM_TITLE",
                    "message": f"Identical explicit room title '{name}' assigned to {count} room polygons."
                })

        unassigned_count = sum(1 for r in rooms if r["name"] == "UNKNOWN_SPACE" or r["status"] == "UNASSIGNED")
        if unassigned_count > 0:
            self.warnings.append({
                "category": "SEMANTICS",
                "code": "UNASSIGNED_ROOM_LABELS",
                "message": f"{unassigned_count} room polygons lack explicit DXF text callouts and were designated UNKNOWN_SPACE."
            })

    def _validate_apertures(self):
        doors = self.data["building_components"].get("doors", [])
        windows = self.data["building_components"].get("windows", [])
        walls = {w["wall_id"]: w for w in self.data["building_components"].get("walls", [])}
        
        for d in doors:
            host = d["host_wall_id"]
            if host not in walls:
                self.blocking_errors.append({
                    "category": "APERTURES",
                    "code": "UNHOSTED_DOOR",
                    "message": f"Door '{d['opening_id']}' is hosted on non-existent wall '{host}'."
                })
            connects = d.get("connects", [])
            if len(connects) > 2:
                self.blocking_errors.append({
                    "category": "APERTURES",
                    "code": "DOOR_OVERCONNECTED",
                    "message": f"Door '{d['opening_id']}' is connected to more than 2 spaces ({connects})."
                })
                
        for w in windows:
            host = w["host_wall_id"]
            if host not in walls:
                self.blocking_errors.append({
                    "category": "APERTURES",
                    "code": "UNHOSTED_WINDOW",
                    "message": f"Window '{w['opening_id']}' is hosted on non-existent wall '{host}'."
                })

    def _validate_footprint(self):
        footprint = self.data["building_components"].get("building_footprint", {})
        coords = footprint.get("coordinates", [])
        area = footprint.get("area", 0.0)
        
        if not coords or len(coords) < 3 or area <= 0:
            self.blocking_errors.append({
                "category": "FOOTPRINT",
                "code": "INVALID_FOOTPRINT",
                "message": "Building footprint geometry is missing or malformed."
            })
            return

        bbox = self.data["coordinate_system"].get("extents", {})
        bbox_area = bbox.get("width", 1.0) * bbox.get("height", 1.0)
        if bbox_area > 0:
            ratio = area / bbox_area
            if ratio < 0.05:
                self.blocking_errors.append({
                    "category": "FOOTPRINT",
                    "code": "FRAGMENTED_BUILDING_FOOTPRINT",
                    "message": f"Building footprint area covers only {ratio:.1%} of drawing extents."
                })
