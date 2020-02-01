import numpy as np
from scipy.ndimage.interpolation import zoom


def generate(session: str) -> dict:
    np.set_printoptions(threshold=np.nan)
    arr = np.random.uniform(size=(4, 4))
    arr = zoom(arr, 8)
    arr = arr > 0.5
    _map = np.where(arr, 0, 1)
    # _map = np.array_str(arr, max_line_width=500)
    _json = {"session": session, "hexagons": []}
    for row, line in enumerate(_map):
        for col, sym in enumerate(line):
            hexagon = {"x": row, "y": col, "type": str(sym)}
            _json["hexagons"].append(hexagon)
    return _json
