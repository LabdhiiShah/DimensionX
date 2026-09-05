import math


class WallParser:

    def __init__(
        self,
        connection_tolerance=0.25,
        perpendicular_tolerance=0.05,
        angle_tolerance=1.5,
        minimum_length=0.15,
        min_thickness=0.08,
        max_thickness=0.45,
        default_thickness=0.20,
        default_height=3.0
    ):
        self.connection_tolerance = connection_tolerance
        self.perpendicular_tolerance = perpendicular_tolerance
        self.angle_tolerance = angle_tolerance
        self.minimum_length = minimum_length
        self.min_thickness = min_thickness
        self.max_thickness = max_thickness
        self.default_thickness = default_thickness
        self.default_height = default_height

        self.diagnostics = {
            "total_raw_entities": 0,
            "initial_segments": 0,
            "paired_double_line_walls": 0,
            "single_line_fallback_walls": 0,
            "merged_fragments_count": 0,
            "average_confidence_score": 0.0,
            "thickness_distribution": {},
            "warnings": []
        }

    # =========================================================
    # MAIN PARSE FUNCTION
    # =========================================================

    def parse(self, wall_entities):

        self.diagnostics["total_raw_entities"] = len(wall_entities)

        # -----------------------------------------------------
        # STEP 1: Extract Line Segments
        # -----------------------------------------------------

        raw_segments = self.extract_segments(wall_entities)
        self.diagnostics["initial_segments"] = len(raw_segments)

        # -----------------------------------------------------
        # STEP 2: Parallel Line Pairing (Double-Line Wall Extraction)
        # -----------------------------------------------------

        paired_walls, remaining_segments = self.pair_parallel_lines(raw_segments)
        self.diagnostics["paired_double_line_walls"] = len(paired_walls)

        # -----------------------------------------------------
        # STEP 3: Process Single Line Fallbacks
        # -----------------------------------------------------

        single_walls = self.process_single_lines(remaining_segments)
        self.diagnostics["single_line_fallback_walls"] = len(single_walls)

        all_walls = paired_walls + single_walls

        # -----------------------------------------------------
        # STEP 4: Collinear Fragment Merging
        # -----------------------------------------------------

        initial_wall_count = len(all_walls)
        merged_walls = self.merge_collinear_walls(all_walls)
        merged_count = initial_wall_count - len(merged_walls)
        self.diagnostics["merged_fragments_count"] = max(0, merged_count)

        # -----------------------------------------------------
        # STEP 5: Final Property Calculation, Confidence & Transforms
        # -----------------------------------------------------

        final_walls = []
        total_confidence = 0.0
        thickness_dist = {}

        for index, wall in enumerate(merged_walls):

            wall["id"] = f"wall_{index + 1:03d}"

            # Validate & normalize wall thickness
            thickness = self.validate_thickness(wall["properties"]["thickness"])
            wall["properties"]["thickness"] = thickness

            # Format thickness string for distribution report
            thick_str = f"{thickness:.2f}m"
            thickness_dist[thick_str] = thickness_dist.get(thick_str, 0) + 1

            start = wall["geometry"]["start"]
            end = wall["geometry"]["end"]
            height = wall["properties"]["height"]

            # Compute thick Unity cube transforms
            wall["unity_transform"] = self.compute_unity_transform(
                start, end, height, thickness
            )

            # Compute 2D footprint rectangle
            wall["footprint_2d"] = self.compute_footprint_2d(
                start, end, thickness
            )

            # Calculate confidence score
            conf = self.calculate_confidence_score(wall, merged_walls)
            wall["confidence_score"] = round(conf, 2)

            # Filter out tiny residual noise
            if wall["geometry"]["length"] >= self.minimum_length:

                final_walls.append(wall)
                total_confidence += wall["confidence_score"]

            else:

                self.diagnostics["warnings"].append(
                    f"Discarded tiny wall fragment {wall['id']} (length={wall['geometry']['length']}m)"
                )

        # Update diagnostics summary
        if final_walls:

            self.diagnostics["average_confidence_score"] = round(
                total_confidence / len(final_walls), 2
            )

        self.diagnostics["thickness_distribution"] = thickness_dist

        print(f"\n==============================")
        print("PARSER DIAGNOSTICS REPORT")
        print("==============================")
        print(f"Total Raw Entities      : {self.diagnostics['total_raw_entities']}")
        print(f"Initial Segments        : {self.diagnostics['initial_segments']}")
        print(f"Paired Double-Line Walls: {self.diagnostics['paired_double_line_walls']}")
        print(f"Single Line Fallbacks   : {self.diagnostics['single_line_fallback_walls']}")
        print(f"Merged Fragments        : {self.diagnostics['merged_fragments_count']}")
        print(f"Final Logical Walls     : {len(final_walls)}")
        print(f"Average Confidence      : {self.diagnostics['average_confidence_score']}")
        print(f"Thickness Distribution  : {self.diagnostics['thickness_distribution']}")
        if self.diagnostics["warnings"]:
            print(f"Warnings ({len(self.diagnostics['warnings'])}):")
            for w in self.diagnostics["warnings"]:
                print(f"  - {w}")
        print("==============================")

        return final_walls

    # =========================================================
    # EXTRACT SEGMENTS
    # =========================================================

    def extract_segments(self, wall_entities):

        segments = []

        for entity in wall_entities:

            typ = entity.get("type")
            layer = entity.get("layer", "WALLS")

            if typ == "LINE":

                start = entity.get("start")
                end = entity.get("end")

                if start and end:

                    segments.append({
                        "type": "LINE",
                        "layer": layer,
                        "start": start,
                        "end": end
                    })

            elif typ in ["LWPOLYLINE", "POLYLINE"]:

                pts = entity.get("points", [])

                if len(pts) >= 2:

                    for i in range(len(pts) - 1):

                        segments.append({
                            "type": typ,
                            "layer": layer,
                            "start": pts[i],
                            "end": pts[i + 1]
                        })

                    if entity.get("closed", False) and len(pts) > 2:

                        segments.append({
                            "type": typ,
                            "layer": layer,
                            "start": pts[-1],
                            "end": pts[0]
                        })

        return segments

    # =========================================================
    # PARALLEL LINE PAIRING ALGORITHM
    # =========================================================

    def pair_parallel_lines(self, segments):

        paired_walls = []
        used_indices = set()

        n = len(segments)

        for i in range(n):

            if i in used_indices:
                continue

            seg_a = segments[i]
            x1_a, y1_a = seg_a["start"][0], seg_a["start"][1]
            x2_a, y2_a = seg_a["end"][0], seg_a["end"][1]

            dx_a = x2_a - x1_a
            dy_a = y2_a - y1_a
            len_a = math.sqrt(dx_a * dx_a + dy_a * dy_a)

            if len_a < 0.05:
                continue

            angle_a = self.normalize_angle(math.degrees(math.atan2(dy_a, dx_a)))
            ux_a = dx_a / len_a
            uy_a = dy_a / len_a

            best_j = None
            best_dist = float("inf")

            for j in range(i + 1, n):

                if j in used_indices:
                    continue

                seg_b = segments[j]
                x1_b, y1_b = seg_b["start"][0], seg_b["start"][1]
                x2_b, y2_b = seg_b["end"][0], seg_b["end"][1]

                dx_b = x2_b - x1_b
                dy_b = y2_b - y1_b
                len_b = math.sqrt(dx_b * dx_b + dy_b * dy_b)

                if len_b < 0.05:
                    continue

                angle_b = self.normalize_angle(math.degrees(math.atan2(dy_b, dx_b)))

                # Check orientation parallelism (within angle_tolerance)
                angle_diff = abs(angle_a - angle_b)

                if angle_diff > self.angle_tolerance and abs(angle_diff - 180) > self.angle_tolerance:
                    continue

                # Perpendicular offset (thickness distance)
                dist1 = abs((x1_b - x1_a) * uy_a - (y1_b - y1_a) * ux_a)
                dist2 = abs((x2_b - x1_a) * uy_a - (y2_b - y1_a) * ux_a)

                offset = (dist1 + dist2) / 2.0

                if not (self.min_thickness <= offset <= self.max_thickness):
                    continue

                # Check overlap ratio along vector axis
                t_a1, t_a2 = 0.0, len_a
                t_b1 = (x1_b - x1_a) * ux_a + (y1_b - y1_a) * uy_a
                t_b2 = (x2_b - x1_a) * ux_a + (y2_b - y1_a) * uy_a

                min_b, max_b = min(t_b1, t_b2), max(t_b1, t_b2)

                overlap_start = max(t_a1, min_b)
                overlap_end = min(t_a2, max_b)
                overlap_len = overlap_end - overlap_start

                min_len = min(len_a, len_b)

                if overlap_len > 0.3 * min_len:

                    if offset < best_dist:

                        best_dist = offset
                        best_j = j

            if best_j is not None:

                used_indices.add(i)
                used_indices.add(best_j)

                seg_b = segments[best_j]
                thickness = round(best_dist, 4)

                # Calculate midline (centerline)
                centerline_start = [
                    (seg_a["start"][0] + seg_b["start"][0]) / 2.0,
                    (seg_a["start"][1] + seg_b["start"][1]) / 2.0,
                    (seg_a["start"][2] + seg_b["start"][2]) / 2.0 if len(seg_a["start"]) > 2 else 0.0
                ]

                centerline_end = [
                    (seg_a["end"][0] + seg_b["end"][0]) / 2.0,
                    (seg_a["end"][1] + seg_b["end"][1]) / 2.0,
                    (seg_a["end"][2] + seg_b["end"][2]) / 2.0 if len(seg_a["end"]) > 2 else 0.0
                ]

                dx = centerline_end[0] - centerline_start[0]
                dy = centerline_end[1] - centerline_start[1]
                dz = centerline_end[2] - centerline_start[2]

                wall_len = math.sqrt(dx * dx + dy * dy + dz * dz)
                wall_angle = math.degrees(math.atan2(dy, dx))

                wall = {
                    "id": "",
                    "type": "WALL",
                    "detection_mode": "DOUBLE_LINE_PAIRED",
                    "source": {
                        "type": "PAIRED",
                        "layer": seg_a["layer"]
                    },
                    "geometry": {
                        "start": [round(c, 4) for c in centerline_start],
                        "end": [round(c, 4) for c in centerline_end],
                        "midpoint": [
                            round((centerline_start[0] + centerline_end[0]) / 2.0, 4),
                            round((centerline_start[1] + centerline_end[1]) / 2.0, 4),
                            round((centerline_start[2] + centerline_end[2]) / 2.0, 4)
                        ],
                        "length": round(wall_len, 4),
                        "angle_deg": round(wall_angle, 4)
                    },
                    "properties": {
                        "height": self.default_height,
                        "thickness": thickness
                    }
                }

                paired_walls.append(wall)

        remaining_segments = [segments[k] for k in range(n) if k not in used_indices]

        return paired_walls, remaining_segments

    # =========================================================
    # SINGLE LINE FALLBACK PROCESSOR
    # =========================================================

    def process_single_lines(self, segments):

        single_walls = []

        for seg in segments:

            start = seg["start"]
            end = seg["end"]

            x1, y1 = float(start[0]), float(start[1])
            x2, y2 = float(end[0]), float(end[1])
            z1 = float(start[2]) if len(start) > 2 else 0.0
            z2 = float(end[2]) if len(end) > 2 else 0.0

            dx = x2 - x1
            dy = y2 - y1
            dz = z2 - z1

            length = math.sqrt(dx * dx + dy * dy + dz * dz)

            if length < 0.05:
                continue

            angle = math.degrees(math.atan2(dy, dx))

            wall = {
                "id": "",
                "type": "WALL",
                "detection_mode": "SINGLE_LINE_FALLBACK",
                "source": {
                    "type": seg["type"],
                    "layer": seg["layer"]
                },
                "geometry": {
                    "start": [round(x1, 4), round(y1, 4), round(z1, 4)],
                    "end": [round(x2, 4), round(y2, 4), round(z2, 4)],
                    "midpoint": [
                        round((x1 + x2) / 2.0, 4),
                        round((y1 + y2) / 2.0, 4),
                        round((z1 + z2) / 2.0, 4)
                    ],
                    "length": round(length, 4),
                    "angle_deg": round(angle, 4)
                },
                "properties": {
                    "height": self.default_height,
                    "thickness": self.default_thickness
                }
            }

            single_walls.append(wall)

        return single_walls

    # =========================================================
    # COLLINEAR FRAGMENT MERGING
    # =========================================================

    def merge_collinear_walls(self, walls):

        changed = True

        while changed:

            changed = False

            for i in range(len(walls)):

                merged = False

                for j in range(i + 1, len(walls)):

                    if self.can_merge(walls[i], walls[j]):

                        walls[i] = self.merge_walls(walls[i], walls[j])
                        walls.pop(j)

                        changed = True
                        merged = True
                        break

                if merged:
                    break

        return walls

    def can_merge(self, wall_a, wall_b):

        geo_a = wall_a["geometry"]
        geo_b = wall_b["geometry"]

        angle_a = self.normalize_angle(geo_a["angle_deg"])
        angle_b = self.normalize_angle(geo_b["angle_deg"])

        angle_diff = abs(angle_a - angle_b)

        if angle_diff > self.angle_tolerance and abs(angle_diff - 180) > self.angle_tolerance:
            return False

        start_a, end_a = geo_a["start"], geo_a["end"]
        start_b, end_b = geo_b["start"], geo_b["end"]

        dx_a = end_a[0] - start_a[0]
        dy_a = end_a[1] - start_a[1]
        len_a = math.sqrt(dx_a * dx_a + dy_a * dy_a)

        if len_a < 1e-6:
            return False

        ux_a = dx_a / len_a
        uy_a = dy_a / len_a

        perp_dist_b1 = abs((start_b[0] - start_a[0]) * uy_a - (start_b[1] - start_a[1]) * ux_a)
        perp_dist_b2 = abs((end_b[0] - start_a[0]) * uy_a - (end_b[1] - start_a[1]) * ux_a)

        if perp_dist_b1 > self.perpendicular_tolerance or perp_dist_b2 > self.perpendicular_tolerance:
            return False

        t_a1, t_a2 = 0.0, len_a
        t_b1 = (start_b[0] - start_a[0]) * ux_a + (start_b[1] - start_a[1]) * uy_a
        t_b2 = (end_b[0] - start_a[0]) * ux_a + (end_b[1] - start_a[1]) * uy_a

        min_b, max_b = min(t_b1, t_b2), max(t_b1, t_b2)

        if max_b < t_a1 - self.connection_tolerance or min_b > t_a2 + self.connection_tolerance:
            return False

        return True

    def merge_walls(self, wall_a, wall_b):

        start_a = wall_a["geometry"]["start"]
        end_a = wall_a["geometry"]["end"]
        start_b = wall_b["geometry"]["start"]
        end_b = wall_b["geometry"]["end"]

        dx_a = end_a[0] - start_a[0]
        dy_a = end_a[1] - start_a[1]
        len_a = math.sqrt(dx_a * dx_a + dy_a * dy_a)

        ux = dx_a / len_a if len_a > 1e-6 else 1.0
        uy = dy_a / len_a if len_a > 1e-6 else 0.0

        pts = [start_a, end_a, start_b, end_b]
        projected = []

        for p in pts:

            t = (p[0] - start_a[0]) * ux + (p[1] - start_a[1]) * uy
            projected.append((t, p))

        projected.sort(key=lambda item: item[0])

        new_start = projected[0][1]
        new_end = projected[-1][1]

        dx = new_end[0] - new_start[0]
        dy = new_end[1] - new_start[1]
        dz = new_end[2] - new_start[2]

        new_len = math.sqrt(dx * dx + dy * dy + dz * dz)
        new_angle = math.degrees(math.atan2(dy, dx))

        # Use preferred double-line thickness if available
        thick_a = wall_a["properties"]["thickness"]
        thick_b = wall_b["properties"]["thickness"]
        merged_thickness = thick_a if wall_a.get("detection_mode") == "DOUBLE_LINE_PAIRED" else thick_b

        detection_mode = (
            "DOUBLE_LINE_PAIRED"
            if wall_a.get("detection_mode") == "DOUBLE_LINE_PAIRED" or wall_b.get("detection_mode") == "DOUBLE_LINE_PAIRED"
            else "SINGLE_LINE_FALLBACK"
        )

        return {
            "id": wall_a["id"],
            "type": "WALL",
            "detection_mode": detection_mode,
            "source": {
                "type": "MERGED",
                "layer": wall_a["source"]["layer"]
            },
            "geometry": {
                "start": [round(c, 4) for c in new_start],
                "end": [round(c, 4) for c in new_end],
                "midpoint": [
                    round((new_start[0] + new_end[0]) / 2.0, 4),
                    round((new_start[1] + new_end[1]) / 2.0, 4),
                    round((new_start[2] + new_end[2]) / 2.0, 4)
                ],
                "length": round(new_len, 4),
                "angle_deg": round(new_angle, 4)
            },
            "properties": {
                "height": wall_a["properties"]["height"],
                "thickness": merged_thickness
            }
        }

    # =========================================================
    # THICKNESS VALIDATION & STANDARDIZATION
    # =========================================================

    def validate_thickness(self, thickness):

        if thickness < self.min_thickness or thickness > self.max_thickness:

            return self.default_thickness

        # Snap to nearest standard architectural thickness (100mm, 150mm, 200mm, 230mm, 300mm)
        standards = [0.10, 0.15, 0.20, 0.23, 0.30, 0.35, 0.40]

        for std in standards:

            if abs(thickness - std) <= 0.02:

                return std

        return round(thickness, 2)

    # =========================================================
    # CONFIDENCE SCORE COMPUTATION (0.0 TO 1.0)
    # =========================================================

    def calculate_confidence_score(self, wall, all_walls):

        score = 0.0

        # 1. Detection mode (Pairing = +0.40, Single = +0.20)
        if wall.get("detection_mode") == "DOUBLE_LINE_PAIRED":

            score += 0.40

        else:

            score += 0.20

        # 2. Layer source verification (+0.30)
        layer = wall["source"].get("layer", "").upper()

        if "WALL" in layer or "PARTITION" in layer or "MASONRY" in layer:

            score += 0.30

        else:

            score += 0.15

        # 3. Endpoint connection with other walls (+0.15)
        start = wall["geometry"]["start"]
        end = wall["geometry"]["end"]

        connected = False

        for other in all_walls:

            if other["id"] == wall["id"]:
                continue

            ostart = other["geometry"]["start"]
            oend = other["geometry"]["end"]

            for p1 in [start, end]:

                for p2 in [ostart, oend]:

                    dx = p1[0] - p2[0]
                    dy = p1[1] - p2[1]

                    if math.sqrt(dx * dx + dy * dy) <= self.connection_tolerance:

                        connected = True
                        break

                if connected:
                    break

            if connected:
                break

        if connected:

            score += 0.15

        # 4. Standard thickness match (+0.15)
        thickness = wall["properties"]["thickness"]

        if thickness in [0.10, 0.15, 0.20, 0.23, 0.30]:

            score += 0.15

        else:

            score += 0.05

        return min(1.0, score)

    # =========================================================
    # COMPUTE UNITY TRANSFORM (POSITION, ROTATION EULER, SCALE)
    # =========================================================

    def compute_unity_transform(self, start, end, height, thickness):

        x1, y1, z1 = start[0], start[1], start[2]
        x2, y2, z2 = end[0], end[1], end[2]

        dx = x2 - x1
        dy = y2 - y1

        length = math.sqrt(dx * dx + dy * dy)
        angle_deg = math.degrees(math.atan2(dy, dx))

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        cz = (z1 + z2) / 2.0

        unity_pos = {
            "x": round(cx, 4),
            "y": round(cz + (height / 2.0), 4),
            "z": round(cy, 4)
        }

        unity_rot = {
            "x": 0.0,
            "y": round(-angle_deg, 4),
            "z": 0.0
        }

        # Unity scale.z IS the actual detected wall thickness!
        unity_scale = {
            "x": round(length, 4),
            "y": round(height, 4),
            "z": round(thickness, 4)
        }

        return {
            "position": unity_pos,
            "rotation_euler": unity_rot,
            "scale": unity_scale
        }

    # =========================================================
    # COMPUTE 2D FOOTPRINT RECTANGLE
    # =========================================================

    def compute_footprint_2d(self, start, end, thickness):

        x1, y1 = start[0], start[1]
        x2, y2 = end[0], end[1]

        dx = x2 - x1
        dy = y2 - y1

        length = math.sqrt(dx * dx + dy * dy)

        if length < 1e-6:

            return [[x1, y1], [x2, y2], [x2, y2], [x1, y1]]

        ux = dx / length
        uy = dy / length

        nx = -uy
        ny = ux

        half_t = thickness / 2.0

        p1 = [round(x1 + nx * half_t, 4), round(y1 + ny * half_t, 4)]
        p2 = [round(x2 + nx * half_t, 4), round(y2 + ny * half_t, 4)]
        p3 = [round(x2 - nx * half_t, 4), round(y2 - ny * half_t, 4)]
        p4 = [round(x1 - nx * half_t, 4), round(y1 - ny * half_t, 4)]

        return [p1, p2, p3, p4]

    # =========================================================
    # ANGLE NORMALIZATION
    # =========================================================

    def normalize_angle(self, angle):

        angle = angle % 180.0

        if angle < 0:

            angle += 180.0

        if abs(angle - 180.0) < 1e-4:

            angle = 0.0

        return angle