import os
import random as rnd
import networkx as nx

LAYOUTS = {
    "Standard (Prawa strona)": "layout_standard",
    "Centrum": "layout_center",
    "Układ Szeregowy (Liniowy)": "layout_linear",
    "Dwie Płyty (Split Apron)": "layout_two_aprons"
}

def get_layout_path(layout_name):
    """Zwraca ścieżkę do folderu z wybranym układem"""
    folder_name = LAYOUTS.get(layout_name, "layout_standard")
    return os.path.join("data_map", folder_name)

def get_layout_names():
    return list(LAYOUTS.keys())


def apply_maintenance(model, mode):
    """
    Usuwa węzły gate'ów z grafu w zależności od wybranego trybu awarii.
    Działa uniwersalnie dla każdego layoutu.
    """
    if mode == "Brak awarii":
        return

    stands = [n for n, d in model.graph.graph.nodes(data=True) if d.get('type') == 'stand']
    
    stands_sorted_x = sorted(stands, key=lambda n: model.graph.graph.nodes[n]['x'])
    
    to_close = []

    if mode == "Losowa awaria (3 gate'y)":
        if len(stands) > 3:
            to_close = rnd.sample(stands, 3)
            
    elif mode == "Remont połowy sekcji (Co drugi)":
        to_close = stands_sorted_x[::2]
        
    elif mode == "Awaria zasilania (Pierwsze 5)":
        to_close = stands_sorted_x[:5]
        
    elif mode == "Zamknięta skrajna sekcja":
        cutoff = int(len(stands) * 0.75)
        to_close = stands_sorted_x[cutoff:]

    if to_close:
        print(f"🔧 MAINTENANCE: Zamykanie gate'ów: {to_close}")

        for node_id in to_close:
            if node_id in model.graph.graph:
                model.graph.graph.remove_node(node_id)
            if node_id in model.graph.digraph:
                model.graph.digraph.remove_node(node_id)


def apply_taxiway_events(model, event_mode):
    """
    Modyfikuje graf dróg kołowania i zjazdów
    """
    if event_mode == "Brak utrudnień":
        return

    print(f"🚧 EVENT: {event_mode}")
    
    edges_to_remove = []
    
    if event_mode == "Zamknięty Zjazd D":
        edges_to_remove.append((8, 7))
        
    elif event_mode == "Zamknięty Zjazd C":
        edges_to_remove.append((10, 9))
        
    elif event_mode == "Zamknięty Wjazd A (Główny 25)":
        edges_to_remove.append((2, 11))

    elif event_mode == "Zamknięty Wjazd F (Główny 07)":
        edges_to_remove.append((5, 1))

    for u, v in edges_to_remove:
        for u_curr, v_curr in [(u, v), (v, u)]:
            if model.graph.digraph.has_edge(u_curr, v_curr):
                model.graph.digraph.remove_edge(u_curr, v_curr)
            if model.graph.graph.has_edge(u_curr, v_curr):
                model.graph.graph.remove_edge(u_curr, v_curr)