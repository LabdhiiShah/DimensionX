from layer_config import LAYER_KEYWORDS
from layer_config import IGNORE_KEYWORDS


class LayerDetector:

    def __init__(self):

        self.useful_layers = {}

        for category in LAYER_KEYWORDS:
            self.useful_layers[category] = []

        self.ignored_layers = []

        self.unknown_layers = []

    # -------------------------------------------------
    # Normalize Layer Name
    # -------------------------------------------------

    def normalize(self, layer):

        layer = layer.lower().strip()

        layer = layer.replace("-", "_")
        layer = layer.replace(" ", "_")
        layer = layer.replace(".", "_")

        while "__" in layer:
            layer = layer.replace("__", "_")

        return layer

    # -------------------------------------------------
    # Detect Layers
    # -------------------------------------------------

    def detect(self, modelspace):

        visited = set()

        for entity in modelspace:

            layer = entity.dxf.layer

            if layer in visited:
                continue

            visited.add(layer)

            name = self.normalize(layer)

            # ============================================
            # STEP 1 : Useful Layers
            # ============================================

            found = False

            for category, keywords in LAYER_KEYWORDS.items():

                for keyword in keywords:

                    if keyword in name:

                        self.useful_layers[category].append(layer)

                        found = True
                        break

                if found:
                    break

            if found:
                continue

            # ============================================
            # STEP 2 : Ignored Layers
            # ============================================

            ignored = False

            for keyword in IGNORE_KEYWORDS:

                if keyword in name:

                    self.ignored_layers.append(layer)

                    ignored = True
                    break

            if ignored:
                continue

            # ============================================
            # STEP 3 : Unknown Layers
            # ============================================

            self.unknown_layers.append(layer)

        return (
            self.useful_layers,
            self.ignored_layers,
            self.unknown_layers
        )

    # -------------------------------------------------
    # Print Report
    # -------------------------------------------------

    def print_report(self):

        print("\nUseful Layers")

        for category, layers in self.useful_layers.items():
            print(f"{category:15} : {layers}")

        print("\nIgnored Layers")
        print(self.ignored_layers)

        print("\nUnknown Layers")
        print(self.unknown_layers)

    # -------------------------------------------------
    # Get All Useful Layers Together
    # -------------------------------------------------

    def get_all_useful_layers(self):

        layers = []

        for category in self.useful_layers.values():
            layers.extend(category)

        return list(set(layers))