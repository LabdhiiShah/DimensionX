import json


class JsonWriter:

    def save(
        self,
        filepath,
        walls,
        classified_entities,
        dxf_filename="drawing.dxf",
        useful_layers=None,
        diagnostics=None
    ):
        doors_raw = classified_entities.get("doors", [])
        windows_raw = classified_entities.get("windows", [])

        doors = self.format_openings(doors_raw, "door", default_height=2.1, default_width=0.9)
        windows = self.format_openings(windows_raw, "window", default_height=1.2, default_width=1.5)

        bounds = self.calculate_bounds(walls)

        output_data = {
            "metadata": {
                "dxf_file": dxf_filename,
                "units": "meters",
                "counts": {
                    "walls": len(walls),
                    "doors": len(doors),
                    "windows": len(windows)
                },
                "bounds": bounds,
                "useful_layers": useful_layers or {}
            },
            "diagnostics": diagnostics or {},
            "unity_config": {
                "coordinate_mapping": "DXF(X, Y, Z) -> Unity(X, Elevation_Z + Height/2, Y)",
                "default_wall_height": 3.0,
                "default_wall_thickness": 0.20
            },
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "raw_entities": classified_entities
        }

        with open(filepath, "w") as f:
            json.dump(output_data, f, indent=4)

        print(f"\nJSON Saved Successfully to: {filepath}")

    def format_openings(self, raw_items, prefix, default_height, default_width):

        items = []

        for idx, item in enumerate(raw_items):

            pos = item.get("position", item.get("start", [0.0, 0.0, 0.0]))

            x = float(pos[0]) if len(pos) > 0 else 0.0
            y = float(pos[1]) if len(pos) > 1 else 0.0
            z = float(pos[2]) if len(pos) > 2 else 0.0

            formatted = {
                "id": f"{prefix}_{idx + 1:03d}",
                "layer": item.get("layer", prefix.upper()),
                "type": item.get("type", "UNKNOWN"),
                "position": [round(x, 4), round(y, 4), round(z, 4)],
                "unity_transform": {
                    "position": {
                        "x": round(x, 4),
                        "y": round(z + (default_height / 2.0), 4),
                        "z": round(y, 4)
                    },
                    "rotation_euler": {
                        "x": 0.0,
                        "y": round(-float(item.get("rotation", 0.0)), 4),
                        "z": 0.0
                    },
                    "scale": {
                        "x": default_width,
                        "y": default_height,
                        "z": 0.15
                    }
                }
            }

            items.append(formatted)

        return items

    def calculate_bounds(self, walls):

        if not walls:

            return {
                "min": [0.0, 0.0, 0.0],
                "max": [0.0, 0.0, 0.0],
                "center": [0.0, 0.0, 0.0]
            }

        min_x = float("inf")
        min_y = float("inf")
        min_z = float("inf")

        max_x = float("-inf")
        max_y = float("-inf")
        max_z = float("-inf")

        for wall in walls:

            start = wall["geometry"]["start"]
            end = wall["geometry"]["end"]

            for pt in [start, end]:

                min_x = min(min_x, pt[0])
                min_y = min(min_y, pt[1])
                min_z = min(min_z, pt[2])

                max_x = max(max_x, pt[0])
                max_y = max(max_y, pt[1])
                max_z = max(max_z, pt[2])

        center_x = round((min_x + max_x) / 2.0, 4)
        center_y = round((min_y + max_y) / 2.0, 4)
        center_z = round((min_z + max_z) / 2.0, 4)

        return {
            "min": [round(min_x, 4), round(min_y, 4), round(min_z, 4)],
            "max": [round(max_x, 4), round(max_y, 4), round(max_z, 4)],
            "center": [center_x, center_y, center_z]
        }