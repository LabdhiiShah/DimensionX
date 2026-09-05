import matplotlib.pyplot as plt


class Visualizer:

    def show_walls(self, walls, raw_wall_entities=None, save_path=None, block=True):

        if not walls:
            print("No logical walls to visualize.")
            return

        print(f"Visualizing {len(walls)} logical walls...")

        if raw_wall_entities is not None:

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 9))

            # ---------------------------------------------
            # Subplot 1: Raw Extracted DXF Lines
            # ---------------------------------------------

            for entity in raw_wall_entities:

                if entity.get("type") == "LINE":

                    s = entity.get("start", [0, 0])
                    e = entity.get("end", [0, 0])

                    ax1.plot([s[0], e[0]], [s[1], e[1]], color="red", linewidth=1.5)

                elif entity.get("type") in ["LWPOLYLINE", "POLYLINE"]:

                    pts = entity.get("points", [])

                    if len(pts) >= 2:

                        px = [p[0] for p in pts]
                        py = [p[1] for p in pts]

                        if entity.get("closed"):

                            px.append(pts[0][0])
                            py.append(pts[0][1])

                        ax1.plot(px, py, color="orange", linewidth=1.5)

            ax1.set_title(f"Raw DXF Extracted Wall Lines ({len(raw_wall_entities)} Entities)")
            ax1.set_xlabel("X Coordinate (m)")
            ax1.set_ylabel("Y Coordinate (m)")
            ax1.axis("equal")
            ax1.grid(True, linestyle="--", alpha=0.4)

            # ---------------------------------------------
            # Subplot 2: Parsed 3D-Ready Logical Walls
            # ---------------------------------------------

            for wall in walls:

                geometry = wall["geometry"]
                start = geometry["start"]
                end = geometry["end"]

                x1, y1 = start[0], start[1]
                x2, y2 = end[0], end[1]

                footprint = wall.get("footprint_2d")

                if footprint and len(footprint) == 4:

                    poly_x = [pt[0] for pt in footprint] + [footprint[0][0]]
                    poly_y = [pt[1] for pt in footprint] + [footprint[0][1]]
                    ax2.fill(poly_x, poly_y, alpha=0.35, color="steelblue")

                ax2.plot([x1, x2], [y1, y2], color="darkblue", linewidth=2)

                wall_id = wall.get("id", "")

                if wall_id:

                    mid_x = (x1 + x2) / 2.0
                    mid_y = (y1 + y2) / 2.0
                    ax2.text(mid_x, mid_y, wall_id, fontsize=7, color="darkred", ha="center")

            ax2.set_title(f"Parsed 3D-Ready Logical Walls ({len(walls)} Walls)")
            ax2.set_xlabel("X Coordinate (m)")
            ax2.set_ylabel("Y Coordinate (m)")
            ax2.axis("equal")
            ax2.grid(True, linestyle="--", alpha=0.4)

        else:

            fig, ax = plt.subplots(figsize=(12, 10))

            for wall in walls:

                geometry = wall["geometry"]
                start = geometry["start"]
                end = geometry["end"]

                x1, y1 = start[0], start[1]
                x2, y2 = end[0], end[1]

                footprint = wall.get("footprint_2d")

                if footprint and len(footprint) == 4:

                    poly_x = [pt[0] for pt in footprint] + [footprint[0][0]]
                    poly_y = [pt[1] for pt in footprint] + [footprint[0][1]]
                    ax.fill(poly_x, poly_y, alpha=0.35, color="steelblue")

                ax.plot([x1, x2], [y1, y2], color="darkblue", linewidth=2)

                wall_id = wall.get("id", "")

                if wall_id:

                    mid_x = (x1 + x2) / 2.0
                    mid_y = (y1 + y2) / 2.0
                    ax.text(mid_x, mid_y, wall_id, fontsize=7, color="darkred", ha="center")

            ax.set_title(f"Parsed 3D-Ready Logical Walls ({len(walls)} Walls)")
            ax.set_xlabel("X Coordinate (m)")
            ax.set_ylabel("Y Coordinate (m)")
            ax.axis("equal")
            ax.grid(True, linestyle="--", alpha=0.4)

        plt.tight_layout()

        if save_path:

            plt.savefig(save_path, dpi=300)
            print(f"Saved visualization image to: {save_path}")

        if block:

            plt.show()

        else:

            plt.close()