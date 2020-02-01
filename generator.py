import numpy as np
from scipy.ndimage.interpolation import zoom
# from pprint import pprint


list_of_candidates = ["101", "103", "104"]
probability_distribution = [0.84, 0.1, 0.06]


def get_type():
    return np.random.choice(list_of_candidates, p=probability_distribution)


def generate(session: str) -> dict:
    np.set_printoptions(threshold=np.nan)
    arr = np.random.uniform(size=(4, 4))
    arr = zoom(arr, 8)
    arr = arr > 0.5
    _map = np.where(arr, 0, 1)
    # _map = np.array_str(arr, max_line_width=500)
    _json = {
        "session": session,
        "hexagons": [
            {
                "x": row,
                "y": col,
                "type": get_type(),
                "player": "",
                "attributes": {}
            }
            for row, line in enumerate(_map)
            for col, sym in enumerate(line)
            if sym != 0
        ]
    }
    return _json


# pprint(generate("123"))
