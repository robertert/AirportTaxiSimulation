import os
import random as rnd
import pandas as pd

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

def get_gates_list(layout_name):
    """
    Zwraca listę słowników {'value': id, 'label': name} dla wszystkich gate'ów w danym layoutcie.
    Używane do wypełnienia listy w Solara.
    """
    path = get_layout_path(layout_name)
    nodes_file = os.path.join(path, "nodes.csv")
    
    if not os.path.exists(nodes_file):
        return []
        
    try:
        df = pd.read_csv(nodes_file)
        stands = df[df['type'] == 'stand']
        return [{"value": row['id'], "label": f"{row['name']} (ID: {row['id']})"} for _, row in stands.iterrows()]
    except Exception as e:
        print(f"Błąd odczytu gate'ów: {e}")
        return []

def apply_maintenance(model, mode, manual_ids=[]):
    """
    Usuwa węzły gate'ów.
    Dodano argument manual_ids dla ręcznego wyboru.
    """
    if mode == "Brak awarii":
        return

    stands = [n for n, d in model.graph.graph.nodes(data=True) if d.get('type') == 'stand']
    stands_sorted_x = sorted(stands, key=lambda n: model.graph.graph.nodes[n]['x'])
    
    to_close = []

    if mode == "Wybór ręczny":
        to_close = [sid for sid in manual_ids if sid in stands]

    elif mode == "Losowa awaria (3 gate'y)":
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