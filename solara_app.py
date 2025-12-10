"""
Interaktywna wizualizacja symulacji lotniska z Mesa i Solara
"""
import solara
from matplotlib.figure import Figure
from src.model import AirportModel
import matplotlib.pyplot as plt
import time
from matplotlib.collections import LineCollection
import numpy as np


# Brak globalnych zmiennych - wszystko jest w komponencie Page


def create_initial_model(num_arriving, wind_direction, arrival_rate):
    """Tworzy nowy model"""
    return AirportModel(
        num_arriving_airplanes=num_arriving,
        wind_direction=wind_direction,
        arrival_rate=arrival_rate
    )



@solara.component
def AirportNetworkViz(model, update_trigger=0):
    # Wymuszamy reaktywność
    _ = update_trigger
    
    # 1. OPTYMALIZACJA: Mniejszy rozmiar i DPI dla szybszego przesyłania
    fig = Figure(figsize=(10, 8), dpi=80) 
    ax = fig.add_subplot(111)
    
    # Ustawienia wykresu
    ax.set_xlim(-2, 71)
    ax.set_ylim(-2, 38)
    ax.set_aspect('equal')
    ax.set_title(f'Symulacja (Krok: {model.step_count})', fontsize=12, fontweight='bold')
    
    # Wyłączamy osie i siatkę dla wydajności (opcjonalne, ale pomaga)
    ax.axis('off') 
    
    # --- RYSOWANIE KRAWĘDZI (WSADOWE - BARDZO SZYBKIE) ---
    edge_types = {
        'runway': {'color': '#2c2c2c', 'width': 4, 'lines': []},
        'taxiway': {'color': '#808080', 'width': 2, 'lines': []},
        'stand_link': {'color': '#32CD32', 'width': 1, 'lines': []},
        'apron_link': {'color': '#4169E1', 'width': 1.5, 'lines': []},
        'other': {'color': '#FF8C00', 'width': 1, 'lines': []}
    }
    
    # Szybkie pobieranie pozycji bez wielokrotnego wyszukiwania w grafie
    # Zakładamy, że struktura grafu się nie zmienia (cache'owanie pozycji)
    # Jeśli węzły są statyczne, można by to obliczyć raz poza funkcją, ale tu zrobimy to lokalnie
    pos = {n: (d['x'], d['y']) for n, d in model.graph.graph.nodes(data=True)}
    
    for u, v, data in model.graph.graph.edges(data=True):
        if u in pos and v in pos:
            p1 = pos[u]
            p2 = pos[v]
            etype = data.get('type', 'taxi')
            
            # Przypisanie do odpowiedniej kategorii
            key = 'other'
            if etype == 'runway': key = 'runway'
            elif etype == 'taxiway': key = 'taxiway'
            elif etype == 'stand_link': key = 'stand_link'
            elif etype == 'apron_link': key = 'apron_link'
            
            edge_types[key]['lines'].append((p1, p2))

    # Rysujemy kolekcje linii (dużo szybsze niż plot w pętli)
    for etype, styles in edge_types.items():
        if styles['lines']:
            lc = LineCollection(styles['lines'], colors=styles['color'], 
                                linewidths=styles['width'], alpha=0.8, zorder=1)
            ax.add_collection(lc)

    # --- RYSOWANIE WĘZŁÓW (WSADOWE) ---
    node_groups = {
        "runway_thr": {"x": [], "y": [], "c": "#2c2c2c", "s": 150, "m": 's'},
        "stand":      {"x": [], "y": [], "c": "#32CD32", "s": 100, "m": 'o'},
        "apron":      {"x": [], "y": [], "c": "#4169E1", "s": 120, "m": 'D'},
        "taxiway":    {"x": [], "y": [], "c": "#808080", "s": 60,  "m": '^'}, # Mniejsze taxiway
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

    # --- RYSOWANIE SAMOLOTÓW (ZOSTAWIAMY PĘTLĘ, BO JEST ICH MAŁO I SĄ SKOMPLIKOWANE) ---
    waiting_offset = 0
    
    # Prealokacja list dla batchowania samolotów (opcjonalnie, tu zostawiamy pętlę dla czytelności logiki)
    for airplane in model.airplanes:
        if airplane.state == "waiting_landing" and airplane.current_node is None:
            x, y = -1, 30 - waiting_offset
            waiting_offset += 2
        else:
            x, y = airplane.get_position()
            
        color = airplane.get_color()
        # Uproszczona logika markerów
        marker = 'v' if airplane.state == "landing" else 'o'
        
        # Rysujemy samolot
        ax.scatter(x, y, c=color, s=180, marker=marker, 
                  edgecolors='black', linewidth=1.5, zorder=5)
        
        # OPTYMALIZACJA: Tekst jest bardzo kosztowny w Matplotlib.
        # Rysujemy go tylko dla samolotów, prostszą metodą (bez boxa jeśli tnie)
        ax.text(x, y-0.8, f'{airplane.unique_id}', 
                fontsize=8, fontweight='bold', ha='center', va='top', zorder=6)

    solara.FigureMatplotlib(fig)


@solara.component
def StatesChart(model, update_trigger=0):
    """Wykres słupkowy ze stanami samolotów"""
    # update_trigger to zależność do triggerowania re-renderu
    _ = update_trigger  # Użyj wartości aby komponent był reaktywny
    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    
    states = {
        'Oczek.\nlądow.': len([a for a in model.airplanes if a.state == 'waiting_landing']),
        'Lądują': len([a for a in model.airplanes if a.state == 'landing']),
        'Taxi→\nstand': len([a for a in model.airplanes if a.state == 'taxiing_to_stand']),
        'Na\nstanow.': len([a for a in model.airplanes if a.state == 'at_stand']),
        'Taxi→\npas': len([a for a in model.airplanes if a.state == 'taxiing_to_runway']),
        'Oczek.\nstart': len([a for a in model.airplanes if a.state == 'waiting_departure']),
        'Startują': len([a for a in model.airplanes if a.state == 'departing']),
    }
    
    colors = ['blue', 'red', 'orange', 'green', 'yellow', 'purple', 'magenta']
    bars = ax.bar(states.keys(), states.values(), color=colors, edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('Liczba samolotów', fontsize=12, fontweight='bold')
    ax.set_title('Stany samolotów', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(states.values()) + 2 if states.values() else 10)
    ax.grid(axis='y', alpha=0.3)
    
    # Dodaj wartości nad słupkami
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    solara.FigureMatplotlib(fig)


@solara.component
def ControlPanel(current_model, step_count, is_playing, simulation_speed):
    """Panel sterowania symulacją"""
    num_arriving = solara.use_reactive(5)
    wind_direction = solara.use_reactive("25")
    arrival_rate = solara.use_reactive(0.02)
    
    with solara.Card("⚙️ Parametry symulacji"):
        solara.SliderInt("Początkowa liczba przylotów", value=num_arriving, min=0, max=20)
        solara.Select("Kierunek wiatru (pas)", value=wind_direction, values=["07", "25"])
        solara.SliderFloat("Częstotliwość przylotów", value=arrival_rate, min=0.0, max=1.0, step=0.01)
        
        # Suwak szybkości symulacji (w milisekundach między krokami)
        solara.Markdown("**⚡ Szybkość symulacji:**")
        solara.SliderFloat(
            "Czas między krokami (ms)", 
            value=simulation_speed, 
            min=50.0, 
            max=2000.0, 
            step=50.0
        )
        solara.Markdown(f"*Aktualna szybkość: {simulation_speed.value:.0f} ms/krok*")
        
        with solara.Row():
            solara.Button("🔄 Restart symulacji", on_click=lambda: reset_simulation(
                num_arriving.value, wind_direction.value, arrival_rate.value,
                current_model, step_count, is_playing
            ))
            
            solara.Button("▶️ Start" if not is_playing.value else "⏸️ Pauza", 
                         on_click=lambda: is_playing.set(not is_playing.value))
            
@solara.component
def ServiceTimeChart(model, update_trigger=0):
    # Wymuszenie odświeżenia
    _ = update_trigger
    
    # Pobieramy dane z DataCollectora
    # Zwraca DataFrame z historią wszystkich kroków
    df = model.datacollector.get_model_vars_dataframe()
    
    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    
    if "Avg_Service_Time" in df.columns and not df.empty:
        # Rysujemy linię
        # df.index to numer kroku, df["Avg_Service_Time"] to wartość
        ax.plot(df.index, df["Avg_Service_Time"], color='purple', linewidth=2)
        
        # Ostatnia wartość jako tekst
        last_val = df["Avg_Service_Time"].iloc[-1]
        ax.set_title(f'Średni czas obsługi: {last_val:.1f} kroków', fontsize=12, fontweight='bold')
    else:
        ax.set_title('Oczekiwanie na pierwszy odlot...', fontsize=12)
        
    ax.set_xlabel('Czas symulacji (kroki)')
    ax.set_ylabel('Średnia liczba kroków')
    ax.grid(True, alpha=0.3)
    
    solara.FigureMatplotlib(fig)
            

def reset_simulation(num_arriving, wind_dir, arr_rate, current_model, step_count, is_playing):
    """Resetuje symulację"""
    model = create_initial_model(num_arriving, wind_dir, arr_rate)
    current_model.set(model)
    step_count.set(0)
    is_playing.set(False)


def step_simulation(current_model, step_count):
    """Wykonuje jeden krok symulacji"""
    if current_model.value:
        current_model.value.step()
        step_count.set(step_count.value + 1)


@solara.component
def InfoPanel(model, update_trigger=0):
    """Panel informacyjny"""
    # update_trigger to zależność do triggerowania re-renderu
    _ = update_trigger  # Użyj wartości aby komponent był reaktywny
    with solara.Card("📊 Status symulacji"):
        runway_status = "🔴 ZAJĘTY" if model.runway_controller.is_busy else "🟢 WOLNY"
        queue_length = model.runway_controller.get_runway_queue_length()
        
        solara.Markdown(f"""
**Krok symulacji:** {model.step_count}

**Wiatr:** RWY {model.wind_direction}  
**Aktywny pas:** {model.runway_controller.active_runway}

**Status pasa:** {runway_status}  
**Długość kolejki:** {queue_length}

**Samolotów w symulacji:** {len(model.airplanes)}
        """)

@solara.component
def Page():
    """Główna strona aplikacji"""
    
    current_model = solara.use_reactive(None)
    step_count = solara.use_reactive(0)
    is_playing = solara.use_reactive(False)
    simulation_speed = solara.use_reactive(50.0) 
    
    # Timer do triggerowania aktualizacji wizualnej
    viz_trigger = solara.use_reactive(0)
    
    if current_model.value is None:
        model = create_initial_model(5, "07", 0.05)
        current_model.set(model)
    
    # Definicja workera
    def play_worker():
        last_render_time = 0
        # Maksymalny FPS dla renderowania (np. 10 klatek/s = co 0.1s)
        # Matplotlib jest ciężki, więc nie chcemy renderować częściej niż to konieczne
        MIN_RENDER_INTERVAL = 0.1 

        while is_playing.value:
            if current_model.value:
                # 1. Wykonaj krok logiczny modelu (to jest szybkie)
                current_model.value.step()
                
                # Zwiększamy licznik wewnętrzny modelu (jeśli potrzebny do UI)
                # Ale NIE robimy tu .set(), żeby nie wymuszać renderu za każdym razem
                
                current_time = time.time()
                sleep_time = simulation_speed.value / 1000.0
                
                # 2. Logika Frame Skipping
                # Jeśli symulacja jest ustawiona na bardzo szybko (np. 50ms), 
                # a od ostatniego renderu minęło mało czasu, pomiń odświeżanie UI.
                
                if sleep_time < MIN_RENDER_INTERVAL:
                    # Tryb szybki: aktualizuj UI tylko jeśli minął interwał
                    if current_time - last_render_time > MIN_RENDER_INTERVAL:
                        step_count.set(current_model.value.step_count) # Aktualizuj licznik
                        viz_trigger.set(viz_trigger.value + 1)       # Wymuś render
                        last_render_time = current_time
                else:
                    # Tryb wolny: aktualizuj UI za każdym krokiem (1:1)
                    step_count.set(current_model.value.step_count)
                    viz_trigger.set(viz_trigger.value + 1)
                    last_render_time = current_time
            
            # Czekaj tyle ile użytkownik ustawił
            time.sleep(simulation_speed.value / 1000.0)

    # WAŻNE: Usunięto simulation_speed.value z dependencies!
    # Dzięki temu zmiana prędkości nie resetuje wątku, a pętla while i tak
    # czyta nową wartość .value w następnym obiegu.
    solara.use_thread(play_worker, dependencies=[is_playing.value])
    
    with solara.Column():
        solara.Title("🛫 Symulacja Lotniska Balice")
        
        ControlPanel(current_model, step_count, is_playing, simulation_speed)
        
        if current_model.value:
            with solara.Columns([2, 1]):
                with solara.Column():
                    # Używamy viz_trigger do odświeżania wykresów
                    AirportNetworkViz(current_model.value, update_trigger=viz_trigger.value)
                    StatesChart(current_model.value, update_trigger=viz_trigger.value)
                    ServiceTimeChart(current_model.value, update_trigger=viz_trigger.value)
                
                with solara.Column():
                    # InfoPanel też podpinamy pod rzadsze odświeżanie
                    InfoPanel(current_model.value, update_trigger=viz_trigger.value)
        else:
            solara.Warning("Model nie został zainicjalizowany")