class EntityClassifier:

    def classify(self, entities, useful_layers):

        result = {

            "walls": [],
            "doors": [],
            "windows": [],
            "stairs": [],
            "columns": [],
            "furniture": [],
            "room_text": [],
            "electrical": [],
            "plumbing": [],
            "unknown": []

        }

        # -----------------------------
        # Layer -> Category lookup
        # -----------------------------

        layer_to_category = {}

        for category, layers in useful_layers.items():

            for layer in layers:

                layer_to_category[layer] = category

        # -----------------------------
        # Classify entities
        # -----------------------------

        for entity in entities:

            layer = entity["layer"]

            category = layer_to_category.get(layer)

            if category is None:

                result["unknown"].append(entity)

            else:

                result[category].append(entity)

        return result