# ==========================================
# layer_config.py
# ==========================================

# Layers that we WANT to detect
LAYER_KEYWORDS = {

    # ---------------- WALLS ----------------

    "walls": [
        "wall",
        "walls",
        "partition",
        "brick",
        "masonry",
        "blockwall",
        "extwall",
        "intwall"
    ],

    # ---------------- DOORS ----------------

    "doors": [
        "door",
        "doors",
        "doorframe",
        "door_frame",
        "frame",
        "dr"
    ],

    # ---------------- WINDOWS ----------------

    "windows": [
        "window",
        "windows",
        "win",
        "glass",
        "gl",
        "elwin"
    ],

    # ---------------- STAIRS ----------------

    "stairs": [
        "stair",
        "stairs",
        "step",
        "staircase"
    ],

    # ---------------- COLUMNS ----------------

    "columns": [
        "column",
        "columns",
        "col",
        "pillar"
    ],

    # ---------------- FURNITURE ----------------

    "furniture": [
        "furniture",
        "furn",
        "chair",
        "table",
        "bed",
        "sofa",
        "cabinet",
        "wardrobe",
        "desk",
        "sink",
        "toilet",
        "washbasin"
    ],

    # ---------------- ROOM LABELS ----------------

    "room_text": [
        "room",
        "label",
        "text",
        "mtext",
        "name"
    ],

    # ---------------- ELECTRICAL ----------------

    "electrical": [
        "electrical",
        "electric",
        "power",
        "socket",
        "switch",
        "lighting",
        "light"
    ],

    # ---------------- PLUMBING ----------------

    "plumbing": [
        "plumbing",
        "pipe",
        "water",
        "drain",
        "sanitary",
        "sewer"
    ],

    # ---------------- STRUCTURAL STEEL ----------------

    "steel": [
        "steel",
        "beam",
        "girder",
        "joist",
        "deck"
    ],

    # ---------------- CONCRETE ----------------

    "concrete": [
        "conc",
        "concrete",
        "rcc"
    ],

    # ---------------- ROOF / CEILING ----------------

    "roof": [
        "roof",
        "ceiling",
        "slab"
    ]
}


# ==========================================
# Layers that are usually NOT useful
# ==========================================

IGNORE_KEYWORDS = [

    # Dimensions
    "dim",
    "dimension",

    # Center lines
    "center",
    "centre",
    "centerline",

    # Reference lines
    "grid",

    # Hatch patterns
    "hatch",

    # Leaders
    "leader",
    "mleader",

    # Viewports
    "viewport",
    "view",

    # Construction
    "construction",

    # External References
    "xref",

    # AutoCAD default
    "defpoints",

    # Temporary
    "temp",

    # Revision clouds
    "revision",
    "revcloud",

    # Hidden lines
    "hidden"
]