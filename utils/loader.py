# utils/loader.py
from models.railway_graph import RailwayGraph
import os

def load_graph_from_default():
    base = os.path.dirname(os.path.dirname(__file__))
    json_path = os.path.join(base, "data", "kalyan_network.json")
    rg = RailwayGraph()
    rg.load_from_json(json_path)
    return rg
