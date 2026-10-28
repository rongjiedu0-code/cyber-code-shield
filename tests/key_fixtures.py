import json
from pathlib import Path
VECTORS=json.loads(Path(__file__).with_name("key_vectors.json").read_text())
def generate(machine,mode="web"):
    return VECTORS[machine][mode]
