"""
Interaktywna wizualizacja symulacji lotniska z Mesa i Solara
"""
import solara
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt
import time
import sys
import os
import scenarios

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.model import AirportModel

@solara.component
def AirportNetworkViz(model, update_trigger=0):
    _ = update_trigger
    
    fig = Figure(figsize=(10, 4.2), dpi=80) 
    ax = fig.add_subplot(111)

    fig.subplots_adjust(left=0, right=1, top=0.90, bottom=0.05)

    ax.set_xlim(-5, 75)
    ax.set_ylim(-5, 32)
    
    ax.set_aspect('equal')
    ax.set_title(f'Layout: {getattr(model, "layout_name", "Standard")} | Krok: {model.step_count}', fontsize=10)
    ax.axis('off') 
    
    edge_types = {
        'runway': {'color': '#2c2c2c', 'width': 4, 'lines': []},
        'taxiway': {'color': '#808080', 'width': 2, 'lines': []},
        'stand_link': {'color': '#32CD32', 'width': 1, 'lines': []},
        'apron_link': {'color': '#4169E1', 'width': 1.5, 'lines': []},
        'other': {'color': '#FF8C00', 'width': 1, 'lines': []}
    }
    
    pos = {n: (d['x'], d['y']) for n, d in model.graph.graph.nodes(data=True)}
    
    for u, v, data in model.graph.graph.edges(data=True):
        if u in pos and v in pos:
            p1 = pos[u]
            p2 = pos[v]
            etype = data.get('type', 'other')
            key = 'other'
            if etype == 'runway': key = 'runway'
            elif etype == 'taxiway': key = 'taxiway'
            elif etype == 'stand_link': key = 'stand_link'
            elif etype == 'apron_link': key = 'apron_link'
            edge_types[key]['lines'].append((p1, p2))

    for etype, styles in edge_types.items():
        if styles['lines']:
            lc = LineCollection(styles['lines'], colors=styles['color'], 
                                linewidths=styles['width'], alpha=0.8, zorder=1)
            ax.add_collection(lc)

    node_groups = {
        "runway_thr": {"x": [], "y": [], "c": "#2c2c2c", "s": 150, "m": 's'},
        "stand":      {"x": [], "y": [], "c": "#32CD32", "s": 100, "m": 'o'},
        "apron":      {"x": [], "y": [], "c": "#4169E1", "s": 120, "m": 'D'},
    }
    
    for n, data in model.graph.graph.nodes(data=True):
        ntype = data.get('type', 'other')
        if ntype in node_groups:
            node_groups[ntype]["x"].append(data['x'])
            node_groups[ntype]["y"].append(data['y'])
    
    for ntype, style in node_groups.items():
        if style["x"]:
            ax.scatter(style["x"], style["y"], c=style["c"], s=style["s"], 
                       marker=style["m"], edgecolors='black', linewidth=0.5, zorder=2, alpha=0.7)
            
    map_labels = [
        {"text": "F", "x": 3, "y": 23},
        {"text": "D", "x": 26, "y": 23},
        {"text": "C", "x": 44, "y": 23},
        {"text": "A", "x": 65, "y": 23},
    ]
    for label in map_labels:
        ax.text(label["x"], label["y"], label["text"],
                fontsize=8, color='#444444', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.6),
                zorder=3)

    for airplane in model.airplanes:
        if airplane.state == "waiting_landing" and airplane.current_node is None:
             pass 
        else:
            x, y = airplane.get_position()
            color = airplane.get_color()
            marker = 'v' if airplane.state == "landing" else 'o'
            ax.scatter(x, y, c=color, s=180, marker=marker, edgecolors='black', zorder=5)
            ax.text(x, y-1.5, f'{airplane.unique_id}', fontsize=7, ha='center', zorder=6)

    solara.FigureMatplotlib(fig)

@solara.component
def StatesChart(model, update_trigger=0):
    _ = update_trigger
    fig = Figure(figsize=(8, 5), dpi=80)
    fig.subplots_adjust(bottom=0.15, top=0.85, left=0.1, right=0.95)
    
    ax = fig.add_subplot(111)
    
    states_count = {
        'Land': len([a for a in model.airplanes if a.state == 'landing']),
        'Taxi': len([a for a in model.airplanes if "taxi" in a.state]),
        'Stand': len([a for a in model.airplanes if a.state == 'at_stand']),
        'Queue': len(model.runway_controller.runway_queue)
    }
    
    ax.bar(states_count.keys(), states_count.values(), color=['red', 'orange', 'green', 'blue'], alpha=0.7)
    ax.set_title("Statystyki", fontsize=10)
    ax.tick_params(axis='both', labelsize=9)
    
    for i, v in enumerate(states_count.values()):
        ax.text(i, v + 0.1, str(v), ha='center', fontsize=9, fontweight='bold')
        
    solara.FigureMatplotlib(fig)

@solara.component
def InfoPanel(model, update_trigger=0):
    """Panel informacyjny"""
    _ = update_trigger  
    
    with solara.Card("📊 Status symulacji"):
        runway_status = "🔴 ZAJĘTY" if model.runway_controller.is_busy else "🟢 WOLNY"
        queue_length = model.runway_controller.get_runway_queue_length()
        
        solara.Markdown(f"""
**Krok symulacji:** {model.step_count}
**Wiatr:** RWY {model.wind_direction}  
**Aktywny pas:** {model.runway_controller.active_runway}
---
**Status pasa:** {runway_status}  
**Długość kolejki do pasa:** {queue_length}
---
**Samolotów w symulacji:** {len(model.airplanes)}
        """)

@solara.component
def ControlPanel(current_model, step_trigger, is_playing, simulation_speed):
    selected_layout = solara.use_reactive("Standard (Lewa strona)")
    maintenance_mode = solara.use_reactive("Brak awarii")

    taxiway_event = solara.use_reactive("Brak utrudnień")
    event_options = [
        "Brak utrudnień",
        "Zamknięty Zjazd D",
        "Zamknięty Zjazd C",
        "Zamknięty Wjazd A (Główny 25)",
        "Zamknięty Wjazd F (Główny 07)"
    ]

    maintenance_options = [
        "Brak awarii", "Losowa awaria (3 gate'y)", "Remont połowy sekcji (Co drugi)", 
        "Awaria zasilania (Pierwsze 5)", "Zamknięta skrajna sekcja"
    ]

    num_arriving = solara.use_reactive(5)
    wind_direction = solara.use_reactive("25")
    arrival_rate = solara.use_reactive(0.05)
    
    with solara.Card("🛠️ Konfiguracja"):
        solara.Markdown("### 1. Infrastruktura")
        solara.Select(label="Układ Lotniska", value=selected_layout, values=scenarios.get_layout_names())
        solara.Select(label="Status Techniczny (Gate'y)", value=maintenance_mode, values=maintenance_options)
        
        solara.Select(label="Zdarzenia Drogowe (Pas/Taxi)", value=taxiway_event, values=event_options)
        
        solara.Markdown("---")
        
        solara.Markdown("### 2. Parametry Ruchu")
        solara.SliderInt("Początkowe samoloty", value=num_arriving, min=0, max=15)
        solara.Select("Kierunek wiatru", value=wind_direction, values=["07", "25"])
        solara.SliderFloat("Częstotliwość przylotów", value=arrival_rate, min=0.0, max=0.5, step=0.01)
        
        solara.Markdown("---")
        
        solara.Markdown("### 3. Sterowanie")
        solara.SliderFloat("Szybkość (ms)", value=simulation_speed, min=50, max=1000)
        
        with solara.Row():
            solara.Button("🔄 Zastosuj i Restartuj", color="primary", on_click=lambda: restart_full(
                current_model, step_trigger, is_playing,
                selected_layout.value, 
                maintenance_mode.value,
                taxiway_event.value,
                num_arriving.value, wind_direction.value, arrival_rate.value
            ))
            
            solara.Button("▶️ Start/Pauza", on_click=lambda: is_playing.set(not is_playing.value))



def restart_full(current_model, step_trigger, is_playing, layout_name, maint_mode, event_mode, num_arr, wind, rate):
    """Tworzy nowy model z pełną konfiguracją"""
    is_playing.set(False)
    
    layout_path = scenarios.get_layout_path(layout_name)
    nodes_file = os.path.join(layout_path, "nodes.csv")
    edges_file = os.path.join(layout_path, "edges.csv")
    
    if not os.path.exists(nodes_file):
        nodes_file = "data/layout_standard/nodes.csv"
        edges_file = "data/layout_standard/edges.csv"
        
    print(f"Start: {layout_name} | Maint: {maint_mode} | Event: {event_mode}")
    
    new_model = AirportModel(
        num_arriving_airplanes=num_arr,
        wind_direction=wind,
        arrival_rate=rate,
        nodes_file=nodes_file,
        edges_file=edges_file
    )
    new_model.layout_name = layout_name
    
    scenarios.apply_maintenance(new_model, maint_mode)
    scenarios.apply_taxiway_events(new_model, event_mode)
    
    current_model.set(new_model)
    step_trigger.set(0)


@solara.component
def Page():
    current_model = solara.use_reactive(None)
    step_trigger = solara.use_reactive(0)
    is_playing = solara.use_reactive(False)
    simulation_speed = solara.use_reactive(100.0)
    
    if current_model.value is None:
        restart_full(current_model, step_trigger, is_playing, "Standard (Lewa strona)", "Brak awarii", "Brak utrudnień", 5, "25", 0.05)

    def worker():
        while True:
            if is_playing.value and current_model.value:
                current_model.value.step()
                step_trigger.set(current_model.value.step_count)
            time.sleep(max(0.1, simulation_speed.value / 1000.0))
            
    solara.use_thread(worker, dependencies=[])
    
    with solara.Column(style={"padding": "10px", "max-width": "1400px", "margin": "0 auto"}):
        solara.Title("Symulacja Lotniska")
        
        with solara.Columns([1, 2]):
            ControlPanel(current_model, step_trigger, is_playing, simulation_speed)
            
            if current_model.value:
                with solara.Column(style={"gap": "0px"}):
                    AirportNetworkViz(current_model.value, update_trigger=step_trigger.value)

                    with solara.Columns([1, 1]):
                        StatesChart(current_model.value, update_trigger=step_trigger.value)
                        InfoPanel(current_model.value, update_trigger=step_trigger.value)