"""
2D Diagnostic Visualization Engine
====================================
Generates visual diagnostic outputs:
1. output/diagnostic_debug.png (detailed debug view comparing wall centerlines, nodes, rooms, doors, windows, footprint)
2. output/diagnostic_clean.png (clean presentation-ready architectural floor plan)
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path

class Visualizer2D:
    def __init__(self, house2d_data, geom_results=None, output_dir="output"):
        self.data = house2d_data
        self.geom_results = geom_results or {}
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def render_all(self):
        print("[Visualizer2D] Rendering 2D diagnostic images...")
        debug_path = os.path.join(self.output_dir, "diagnostic_debug.png")
        clean_path = os.path.join(self.output_dir, "diagnostic_clean.png")
        
        self.render_debug(debug_path)
        self.render_clean(clean_path)
        return debug_path, clean_path

    def render_debug(self, filepath):
        fig, ax = plt.subplots(figsize=(14, 12), dpi=150)
        ax.set_aspect('equal')
        ax.set_facecolor('#1e1e24') # dark debug aesthetic
        
        # 1. Building Footprint
        footprint = self.data["building_components"].get("building_footprint", {})
        coords = footprint.get("coordinates", [])
        if coords:
            fp_patch = patches.Polygon(coords, closed=True, facecolor='#2a2a36', edgecolor='#ff4757', linewidth=2, linestyle='--', alpha=0.5, label='Building Footprint')
            ax.add_patch(fp_patch)

        # 2. Room Polygons
        rooms = self.data["building_components"].get("rooms", [])
        colors = ['#1e90ff', '#2ed573', '#ffa502', '#ff6b81', '#70a1ff', '#eccc68']
        for idx, r in enumerate(rooms):
            r_coords = r["polygon_vertices"]
            if r_coords:
                col = colors[idx % len(colors)]
                r_patch = patches.Polygon(r_coords, closed=True, facecolor=col, edgecolor='#ffffff', linewidth=1.5, alpha=0.3)
                ax.add_patch(r_patch)
                
                # Label room center
                xs = [pt[0] for pt in r_coords]
                ys = [pt[1] for pt in r_coords]
                cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
                lbl = f"{r['name']}\n({r['room_id']})"
                ax.text(cx, cy, lbl, color='#ffffff', fontsize=8, fontweight='bold', ha='center', va='center',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='#000000', alpha=0.7))

        # 3. Wall Centerlines
        walls = self.data["building_components"].get("walls", [])
        for w in walls:
            cl = w["centerline"]
            p1, p2 = cl[0], cl[1]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#ffffff', linewidth=2.5, zorder=4)

        # 4. Vertices / Nodes
        vertices = self.data["building_components"].get("vertices", [])
        vx = [v["x"] for v in vertices]
        vy = [v["y"] for v in vertices]
        ax.scatter(vx, vy, color='#fffa65', s=25, zorder=5, label='Welded Junction Nodes')

        # 5. Doors & Windows
        doors = self.data["building_components"].get("doors", [])
        for d in doors:
            cx, cy = d["center"]
            ax.scatter(cx, cy, color='#ff4757', marker='s', s=45, zorder=6, label='Door Aperture' if d == doors[0] else "")
            ax.text(cx, cy+5, d["opening_id"], color='#ff4757', fontsize=7, ha='center')

        windows = self.data["building_components"].get("windows", [])
        for w in windows:
            cx, cy = w["center"]
            ax.scatter(cx, cy, color='#00d2d3', marker='^', s=45, zorder=6, label='Window Aperture' if w == windows[0] else "")
            ax.text(cx, cy-5, w["opening_id"], color='#00d2d3', fontsize=7, ha='center')

        # Metadata & Legend
        units_info = self.data.get("units", {})
        src_name = os.path.basename(self.data['metadata']['source_dxf'])
        title = f"House2D Reconstruction Debug Diagnostic — {src_name}\n" \
                f"Units: {units_info.get('unit_name')} (scale={units_info.get('scale_to_meters')}m) | Walls: {len(walls)} | Rooms: {len(rooms)}"
        ax.set_title(title, color='#ffffff', fontsize=11, fontweight='bold', pad=15)
        ax.grid(True, color='#333344', linestyle=':', linewidth=0.5)
        ax.tick_params(colors='#888899', labelsize=8)
        
        plt.tight_layout()
        from pathlib import Path
        abs_path = str(Path(filepath).resolve())
        try:
            with open(abs_path, 'wb') as f:
                fig.savefig(f, format='png', dpi=150)
            print(f"[Visualizer2D] Generated Debug Diagnostic: {abs_path}")
        except Exception as err:
            print(f"[Visualizer2D] Warning: Could not save debug diagnostic ({err})")
        plt.close(fig)

    def render_clean(self, filepath):
        fig, ax = plt.subplots(figsize=(14, 12), dpi=150)
        ax.set_aspect('equal')
        ax.set_facecolor('#ffffff') # clean white paper aesthetic
        
        # 1. Building Footprint / Slab background
        footprint = self.data["building_components"].get("building_footprint", {})
        coords = footprint.get("coordinates", [])
        if coords:
            fp_patch = patches.Polygon(coords, closed=True, facecolor='#f5f6fa', edgecolor='#718093', linewidth=1.5)
            ax.add_patch(fp_patch)

        # 2. Rooms
        rooms = self.data["building_components"].get("rooms", [])
        for r in rooms:
            r_coords = r["polygon_vertices"]
            if r_coords:
                r_patch = patches.Polygon(r_coords, closed=True, facecolor='#f8f9fa', edgecolor='#dcdde1', linewidth=1.0)
                ax.add_patch(r_patch)
                
                xs = [pt[0] for pt in r_coords]
                ys = [pt[1] for pt in r_coords]
                cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
                
                dim_str = f"\n{r['parsed_dimensions']}" if r.get('parsed_dimensions') else ""
                lbl = f"{r['name']}{dim_str}"
                ax.text(cx, cy, lbl, color='#2f3640', fontsize=9, fontweight='bold', ha='center', va='center')

        # 3. Walls (Black solid lines)
        walls = self.data["building_components"].get("walls", [])
        for w in walls:
            cl = w["centerline"]
            p1, p2 = cl[0], cl[1]
            lw = 3.5 if w["wall_class"] == "EXTERIOR" else 2.0
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#2f3640', linewidth=lw, zorder=4)

        # 4. Doors & Windows
        doors = self.data["building_components"].get("doors", [])
        for d in doors:
            cx, cy = d["center"]
            circle = patches.Circle((cx, cy), radius=8.0, facecolor='#e1b12c', edgecolor='#2f3640', linewidth=1.0, zorder=5)
            ax.add_patch(circle)

        windows = self.data["building_components"].get("windows", [])
        for w in windows:
            cx, cy = w["center"]
            rect = patches.Rectangle((cx-8, cy-4), 16, 8, facecolor='#00a8ff', edgecolor='#2f3640', linewidth=1.0, zorder=5)
            ax.add_patch(rect)

        src_name = os.path.basename(self.data['metadata']['source_dxf'])
        ax.set_title(f"Architectural 2D Reconstruction — {src_name}", color='#2f3640', fontsize=12, fontweight='bold', pad=15)
        ax.axis('off')
        
        plt.tight_layout()
        from pathlib import Path
        abs_path = str(Path(filepath).resolve())
        try:
            with open(abs_path, 'wb') as f:
                fig.savefig(f, format='png', dpi=150)
            print(f"[Visualizer2D] Generated Clean Diagnostic: {abs_path}")
        except Exception as err:
            print(f"[Visualizer2D] Warning: Could not save clean diagnostic ({err})")
        plt.close(fig)
