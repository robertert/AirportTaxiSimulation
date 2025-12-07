import pandas as pd
import os
import networkx as nx

# Konfiguracja ścieżek
BASE_DIR = "data_map"
NODES_SRC = os.path.join(BASE_DIR, "nodes.csv")
EDGES_SRC = os.path.join(BASE_DIR, "edges.csv")

# Stałe geometrii lotniska
RUNWAY_Y = 27
TAXIWAY_B_Y = 20
STANDS_Y_START = 9
APRON_Y_START = 10

# Funkcje pomocnicze
def save_layout(name, nodes_df, edges_df):
    target_dir = os.path.join(BASE_DIR, name)
    os.makedirs(target_dir, exist_ok=True)
    nodes_df.to_csv(os.path.join(target_dir, "nodes.csv"), index=False)
    edges_df.to_csv(os.path.join(target_dir, "edges.csv"), index=False)
    print(f"✅ Utworzono układ: {name}")

def shift_apron_elements(nodes_df, shift_x):
    """Przesuwa całą płytę postojową o zadaną wartość X"""
    new_nodes = nodes_df.copy()
    # Maska dla elementów płyty (poniżej Taxiway B)
    mask = new_nodes['y'] < TAXIWAY_B_Y
    new_nodes.loc[mask, 'x'] += shift_x
    return new_nodes

def create_linear_apron(base_nodes_df, start_x=5, spacing=4):
    """Tworzy płytę z gate'ami w jednym rzędzie (Scenariusz 3)"""
    nodes = base_nodes_df.copy()
    edges = []
    
    # 1. Zachowaj tylko pas, główne taxiway i zjazdy
    nodes = nodes[nodes['y'] >= TAXIWAY_B_Y].copy()
    
    # 2. Znajdź punkty zjazdu z Taxiway B na płytę
    taxiway_b_nodes = nodes[nodes['type'] == 'taxiway']
    
    # 3. Stwórz nowe węzły dla szeregowych gate'ów
    num_stands = 16
    stand_y = 9
    apron_lane_y = 13 # Droga dojazdowa przed gate'ami
    
    new_node_id = nodes['id'].max() + 1
    
    apron_nodes_ids = []
    stand_nodes_ids = []
    
    for i in range(num_stands):
        x = start_x + i * spacing
        
        # Węzeł "uliczki" apronu
        apron_id = new_node_id
        nodes = pd.concat([nodes, pd.DataFrame([{
            'id': apron_id, 'type': 'apron_link', 'name': f'APRON_{i}', 
            'x': x, 'y': apron_lane_y, 'notes': ''
        }])], ignore_index=True)
        apron_nodes_ids.append(apron_id)
        new_node_id += 1
        
        # Węzeł stanowiska (Stand)
        stand_id = new_node_id
        nodes = pd.concat([nodes, pd.DataFrame([{
            'id': stand_id, 'type': 'stand', 'name': f'STAND_{i+1}', 
            'x': x, 'y': stand_y, 'notes': ''
        }])], ignore_index=True)
        stand_nodes_ids.append(stand_id)
        new_node_id += 1
        
        # Krawędź: Apron -> Stand
        edges.append({'from': apron_id, 'to': stand_id, 'type': 'stand_link', 'length': apron_lane_y - stand_y, 'bidirectional': True})
        
        # Krawędź: Apron -> Apron (poprzedni)
        if i > 0:
             prev_apron_id = apron_nodes_ids[i-1]
             edges.append({'from': prev_apron_id, 'to': apron_id, 'type': 'apron_link', 'length': spacing, 'bidirectional': True})

    # 4. Połącz nową "uliczkę" z głównym Taxiway B
    # Znajdź najbliższe węzły na Taxiway B dla początku i końca nowej płyty
    first_apron = apron_nodes_ids[0]
    last_apron = apron_nodes_ids[-1]
    
    # Proste połączenie: znajdź węzły na TWY B o zbliżonym X
    twy_conn_1 = taxiway_b_nodes.iloc[(taxiway_b_nodes['x'] - start_x).abs().argsort()[:1]]['id'].values[0]
    twy_conn_2 = taxiway_b_nodes.iloc[(taxiway_b_nodes['x'] - (start_x + num_stands*spacing)).abs().argsort()[:1]]['id'].values[0]

    edges.append({'from': twy_conn_1, 'to': first_apron, 'type': 'taxiway', 'length': TAXIWAY_B_Y - apron_lane_y, 'bidirectional': True})
    edges.append({'from': twy_conn_2, 'to': last_apron, 'type': 'taxiway', 'length': TAXIWAY_B_Y - apron_lane_y, 'bidirectional': True})
    
    # Dodaj oryginalne krawędzie (pas, twy b)
    orig_edges = pd.read_csv(EDGES_SRC)
    # Filtruj krawędzie, które łączą tylko istniejące węzły
    valid_ids = set(nodes['id'])
    orig_edges_filtered = orig_edges[orig_edges['from'].isin(valid_ids) & orig_edges['to'].isin(valid_ids)]
    
    final_edges = pd.concat([orig_edges_filtered, pd.DataFrame(edges)], ignore_index=True)
    
    return nodes, final_edges

def create_compact_apron(base_nodes_df, center_x=35):
    """Tworzy płytę z dwoma rzędami gate'ów (Scenariusz 4)"""
    nodes = base_nodes_df.copy()
    edges = []
    
    # 1. Zachowaj tylko górną część lotniska
    nodes = nodes[nodes['y'] >= TAXIWAY_B_Y].copy()
    taxiway_b_nodes = nodes[nodes['type'] == 'taxiway']

    num_stands_per_row = 8
    spacing = 4
    row1_y = 9
    apron1_y = 12
    apron2_y = 15
    row2_y = 18
    
    start_x = center_x - (num_stands_per_row * spacing) / 2
    new_node_id = nodes['id'].max() + 1
    
    apron1_ids = []
    apron2_ids = []

    for i in range(num_stands_per_row):
        x = start_x + i * spacing
        
        # Rząd 1 (Dolny)
        stand1_id = new_node_id; new_node_id += 1
        apron1_id = new_node_id; new_node_id += 1
        nodes = pd.concat([nodes, pd.DataFrame([
            {'id': stand1_id, 'type': 'stand', 'x': x, 'y': row1_y},
            {'id': apron1_id, 'type': 'apron_link', 'x': x, 'y': apron1_y}
        ])], ignore_index=True)
        edges.append({'from': apron1_id, 'to': stand1_id, 'type': 'stand_link', 'length': apron1_y - row1_y, 'bidirectional': True})
        apron1_ids.append(apron1_id)
        
        # Rząd 2 (Górny)
        stand2_id = new_node_id; new_node_id += 1
        apron2_id = new_node_id; new_node_id += 1
        nodes = pd.concat([nodes, pd.DataFrame([
            {'id': stand2_id, 'type': 'stand', 'x': x, 'y': row2_y},
            {'id': apron2_id, 'type': 'apron_link', 'x': x, 'y': apron2_y}
        ])], ignore_index=True)
        edges.append({'from': apron2_id, 'to': stand2_id, 'type': 'stand_link', 'length': row2_y - apron2_y, 'bidirectional': True})
        apron2_ids.append(apron2_id)
        
        # Połączenia poziome w rzędach
        if i > 0:
            edges.append({'from': apron1_ids[i-1], 'to': apron1_id, 'type': 'apron_link', 'length': spacing, 'bidirectional': True})
            edges.append({'from': apron2_ids[i-1], 'to': apron2_id, 'type': 'apron_link', 'length': spacing, 'bidirectional': True})
            
        # Połączenia pionowe między rzędami (co kilka stanowisk)
        if i % 3 == 0 or i == num_stands_per_row - 1:
             edges.append({'from': apron1_id, 'to': apron2_id, 'type': 'apron_link', 'length': apron2_y - apron1_y, 'bidirectional': True})

    # Połączenie z Taxiway B (z górnego rzędu apron2)
    # Używamy węzła środkowego TWY B (np. ID 9 - TWY_C_START, x=43)
    twy_conn = 9 # Zakładam, że ID 9 istnieje i jest na środku
    edges.append({'from': twy_conn, 'to': apron2_ids[num_stands_per_row//2], 'type': 'taxiway', 'length': TAXIWAY_B_Y - apron2_y, 'bidirectional': True})

    # Dodaj oryginalne krawędzie
    orig_edges = pd.read_csv(EDGES_SRC)
    valid_ids = set(nodes['id'])
    orig_edges_filtered = orig_edges[orig_edges['from'].isin(valid_ids) & orig_edges['to'].isin(valid_ids)]
    final_edges = pd.concat([orig_edges_filtered, pd.DataFrame(edges)], ignore_index=True)

    return nodes, final_edges


def generate_layouts():
    df_nodes_base = pd.read_csv(NODES_SRC)
    df_edges_base = pd.read_csv(EDGES_SRC)

    # SCENARIUSZ 1: Standard (Lewa strona - jak oryginał)
    # Zakładam, że Twój 'nodes.csv' w 'data/' to jest ten oryginalny z gate'ami po lewej/prawej.
    # Jeśli oryginał ma gate'y po prawej (X > 50), a chcesz "Standard (Lewa strona)", musisz je przesunąć.
    # Sprawdźmy, gdzie są gate'y w bazie.
    mean_stand_x = df_nodes_base[df_nodes_base['type'] == 'stand']['x'].mean()
    
    if mean_stand_x > 35: # Jeśli są po prawej, przesuń w lewo
        nodes_standard = shift_apron_elements(df_nodes_base, shift_x=-45)
    else:
        nodes_standard = df_nodes_base # Już są po lewej

    save_layout("layout_standard", nodes_standard, df_edges_base)

    # SCENARIUSZ 2: Centrum (Przesunięcie na środek)
    # Celujemy w środek mapy (X = 35). Obliczamy potrzebne przesunięcie.
    current_center_x = nodes_standard[nodes_standard['y'] < TAXIWAY_B_Y]['x'].mean()
    shift_to_center = 35 - current_center_x
    nodes_center = shift_apron_elements(nodes_standard, shift_x=shift_to_center)
    save_layout("layout_center", nodes_center, df_edges_base)

    # SCENARIUSZ 3: Szeregowy (Linear)
    nodes_linear, edges_linear = create_linear_apron(df_nodes_base, start_x=5)
    save_layout("layout_linear", nodes_linear, edges_linear)

    # SCENARIUSZ 4: Kompaktowy (Podwójny rząd)
    nodes_compact, edges_compact = create_compact_apron(df_nodes_base)
    save_layout("layout_compact", nodes_compact, edges_compact)


if __name__ == "__main__":
    generate_layouts()