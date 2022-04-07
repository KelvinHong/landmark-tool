import PySimpleGUI as sg
from PIL import Image
import os
import io
from typing import Literal, Tuple
import pandas as pd
import json
import numpy as np

CACHE = "cachefile.json"
ANNOTATION = "annotation/"

INDENT = 4
SPACE = " "
NEWLINE = "\n"

# This program includes software developed by jterrace and David Kim 
# in https://stackoverflow.com/questions/10097477/python-json-array-newlines
# Huge thanks to them!
# Changed basestring to str, and dict uses items() instead of iteritems().
def to_json(o, level=0):
    ret = ""
    if isinstance(o, dict):
        ret += "{" + NEWLINE
        comma = ""
        for k, v in o.items():
            ret += comma
            comma = ",\n"
            ret += SPACE * INDENT * (level + 1)
            ret += '"' + str(k) + '":' + SPACE
            ret += to_json(v, level + 1)

        ret += NEWLINE + SPACE * INDENT * level + "}"
    elif isinstance(o, str):
        ret += '"' + o + '"'
    elif isinstance(o, list):
        ret += "[" + ",".join([to_json(e, level + 1) for e in o]) + "]"
    # Tuples are interpreted as lists
    elif isinstance(o, tuple):
        ret += "[" + ",".join(to_json(e, level + 1) for e in o) + "]"
    elif isinstance(o, bool):
        ret += "true" if o else "false"
    elif isinstance(o, int):
        ret += str(o)
    elif isinstance(o, float):
        ret += '%.7g' % o
    elif isinstance(o, np.ndarray) and np.issubdtype(o.dtype, np.integer):
        ret += "[" + ','.join(map(str, o.flatten().tolist())) + "]"
    elif isinstance(o, np.ndarray) and np.issubdtype(o.dtype, np.inexact):
        ret += "[" + ','.join(map(lambda x: '%.7g' % x, o.flatten().tolist())) + "]"
    elif o is None:
        ret += 'null'
    else:
        raise TypeError("Unknown type '%s' for json serialization" % str(type(o)))
    return ret

def inspect_annotation_json(Dir, num_lm, WINDOW_LOC = (None, None)) -> Tuple[str, bool]:
    annotation_csv = os.path.join(ANNOTATION, os.path.basename(Dir) + ".csv")
    annotation_json = os.path.join(ANNOTATION, os.path.basename(Dir) + ".json")
    
    if not os.path.isfile(annotation_json) or not os.path.isfile(annotation_csv):
        # Create empty json file
        pretty_dump({}, annotation_json)
    # If csv exist, load json from csv.
    # Since we don't know window size yet, only load "xy".
    # Will load "mouse_xy" once StateMachine is initiated.
    if os.path.isfile(annotation_csv):
        dic = {}
        df = pd.read_csv(annotation_csv, header = 0)
        n = len(df)
        for i in range(n):
            row = df.iloc[i]
            xy_data = []
            j = 1
            row_keys = list(row.keys())
            while True:
                if f"x{j}" not in row_keys or pd.isnull(row[f"x{j}"]):
                    break
                xy_data.append([int(row[f"x{j}"]), int(row[f"y{j}"])])
                j += 1
            dic[row["image_name"]] = {"xy": xy_data}
        pretty_dump(dic, annotation_json)
    return annotation_json


def pretty_dump(data: dict, filename: str):
    json_string = to_json(data)
    with open(filename, "w") as f:
        f.write(json_string)
