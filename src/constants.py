# CD. ORIGINAL_LABELS
# original_labels = List[str]
# interp. A list of original labels for classification tasks.
ORIG_LABELS = [
    "aromatics",
    "alcohols", 
    "amines",
    "esters",
    "alkene",
    "carb. acids",
    "ketones",
    "phenol",
    "nitriles",
    "amides",
    "aldehydes",
    "alkyne"
]

# DD. CONFIG_SETTINGS
# config = {"IMAGES_PATH":str}
# interp. A dictionary storing configuration settings for the application.
config = {
    "IMAGES_PATH": "",
    "ANNOTATIONS_PATH": "",
    "PROJECT_LOADED": False,
    "MODEL_PATHS": [],
    "LABELS": [],
    "MODE": "BOX",
}


