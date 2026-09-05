class EntityExtractor:

    def extract(self, msp, useful_layers):

        allowed = set()

        for layer_list in useful_layers.values():
            allowed.update(layer_list)

        entities = []

        for e in msp:

            if e.dxf.layer not in allowed:
                continue

            typ = e.dxftype()

            data = {

                "type": typ,
                "layer": e.dxf.layer

            }

            # ---------------- LINE ----------------

            if typ == "LINE":

                data["start"] = [
                    e.dxf.start.x,
                    e.dxf.start.y,
                    e.dxf.start.z
                ]

                data["end"] = [
                    e.dxf.end.x,
                    e.dxf.end.y,
                    e.dxf.end.z
                ]

            # ---------------- LWPOLYLINE ----------------

            elif typ == "LWPOLYLINE":

                pts = []

                for p in e.get_points():

                    pts.append([

                        p[0],
                        p[1],
                        0

                    ])

                data["points"] = pts
                data["closed"] = e.closed

            # ---------------- POLYLINE ----------------

            elif typ == "POLYLINE":

                pts = []

                for v in e.vertices:

                    pts.append([

                        v.dxf.location.x,
                        v.dxf.location.y,
                        v.dxf.location.z

                    ])

                data["points"] = pts

            # ---------------- ARC ----------------

            elif typ == "ARC":

                data["center"] = [

                    e.dxf.center.x,
                    e.dxf.center.y,
                    e.dxf.center.z

                ]

                data["radius"] = e.dxf.radius

                data["start_angle"] = e.dxf.start_angle
                data["end_angle"] = e.dxf.end_angle

            # ---------------- CIRCLE ----------------

            elif typ == "CIRCLE":

                data["center"] = [

                    e.dxf.center.x,
                    e.dxf.center.y,
                    e.dxf.center.z

                ]

                data["radius"] = e.dxf.radius

            # ---------------- INSERT ----------------

            elif typ == "INSERT":

                data["block_name"] = e.dxf.name

                data["position"] = [

                    e.dxf.insert.x,
                    e.dxf.insert.y,
                    e.dxf.insert.z

                ]

                data["rotation"] = getattr(e.dxf, "rotation", 0)

            # ---------------- TEXT ----------------

            elif typ == "TEXT":

                data["text"] = e.dxf.text

                data["position"] = [

                    e.dxf.insert.x,
                    e.dxf.insert.y,
                    e.dxf.insert.z

                ]

            # ---------------- MTEXT ----------------

            elif typ == "MTEXT":

                data["text"] = e.text

                data["position"] = [

                    e.dxf.insert.x,
                    e.dxf.insert.y,
                    e.dxf.insert.z

                ]

            else:
                continue

            entities.append(data)

        return entities