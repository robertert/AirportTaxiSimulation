#!/usr/bin/env python3
"""
Główny plik uruchamiający symulację lotniska z pasem startowym
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.model import AirportModel
from src.visualization import AirportVisualization
import matplotlib.pyplot as plt


def configure_airport(model: "AirportModel"):
    """
    Konfiguracja jednokierunkowości i segmentów kolejki w oparciu o dane grafu.
    W tym miejscu można ustawić:
    - krawędzie jednokierunkowe (model.graph.set_one_way / set_bidirectional),
    - pojemności segmentów kolejki (model.graph.set_edge_capacity),
    - limity prędkości (model.graph.set_edge_speed_limits),
    - punkty konfliktu (model.graph.add_conflict_point).
    Domyślnie nic nie zmieniamy (mapa może już zawierać te informacje).
    """
    # Przykład (zakomentowane – brak wiedzy o konkretnych ID z CSV):
    # model.graph.set_one_way(12, 15, 'AB')
    # model.graph.set_edge_capacity(21, 22, capacity=3)  # np. segment kolejki
    # model.graph.add_conflict_point(1, description="Crossing RWY", edges=[(30,31), (40,41)])
    return

def scenarios_smoke_tests(model: "AirportModel"):
    """
    Proste scenariusze dymne do ręcznego uruchomienia:
    1) Pushback lock – tylko jeden samolot jednocześnie.
    2) Kolejka: pojemność segmentu (jeśli skonfigurowana).
    3) Pas: blokada podczas operacji.
    """
    print("▶ Scenariusze dymne (manualne):")
    print("- Pushback lock: użyj state 'at_stand' >=2 i obserwuj 'pushback_pending'/'pushback'")
    print("- Kolejki: ustaw capacity na segmencie 'queue' i obserwuj równoległe zajęcia")
    print("- Pas: obserwuj blokadę w statystykach wizualizacji")

def main():
    """Główna funkcja uruchamiająca symulację"""
    print("🛫 Uruchamianie symulacji lotniska Balice...")
    print("=" * 50)
    
    # Parametry symulacji
    num_arriving_airplanes = 3  # Początkowa liczba samolotów przybywających
    wind_direction = "07"  # Kierunek wiatru: "07" lub "25"
    arrival_rate = 0.00  # Prawdopodobieństwo pojawienia się nowego samolotu
    
    print(f"Parametry symulacji:")
    print(f"- Mapa: Graf lotniska (nodes.csv, edges.csv)")
    print(f"- Początkowa liczba przybywających: {num_arriving_airplanes}")
    print(f"- Kierunek wiatru: RWY {wind_direction}")
    print(f"- Częstotliwość przylotów: {arrival_rate}")
    print()
    
    # Tworzenie modelu
    model = AirportModel(
        num_arriving_airplanes=num_arriving_airplanes,
        wind_direction=wind_direction,
        arrival_rate=arrival_rate
    )
    
    # Tworzenie wizualizacji
    viz = AirportVisualization(model)

    # Konfiguracja lotniska (jednokierunkowość, pojemności, konflikty)
    configure_airport(model)

    print("Wybierz tryb uruchomienia:")
    print("1. Animacja interaktywna")
    print("2. Statyczny obraz")
    print("3. Zapisz animację do pliku")
    print("4. Uruchom pełną symulację i pokaż statystyki")
    
    choice = "1"

    if choice == "1":
        print("Uruchamianie animacji interaktywnej...")
        print("Zamknij okno aby zakończyć.")
        anim = viz.animate(frames=1000, interval=500)
        plt.show()
        
    elif choice == "2":
        print("Pokazywanie statycznego obrazu...")
        viz.show_static()
        
    elif choice == "3":
        filename = input("Nazwa pliku (domyślnie: airport_simulation.gif): ").strip()
        if not filename:
            filename = "airport_simulation.gif"
        print(f"Zapisywanie animacji jako {filename}...")
        viz.save_animation(filename, frames=100, interval=500)
        
    elif choice == "4":
        print("Uruchamianie pełnej symulacji...")
        max_steps = 100
        
        # Uruchomienie symulacji
        step_count = 0
        while model.running and step_count < max_steps:
            model.step()
            step_count += 1
            
            if step_count % 10 == 0:
                waiting_landing = len([a for a in model.airplanes if a.state == 'waiting_landing'])
                landing = len([a for a in model.airplanes if a.state == 'landing'])
                at_stand = len([a for a in model.airplanes if a.state == 'at_stand'])
                waiting_dep = len([a for a in model.airplanes if a.state == 'waiting_departure'])
                departing = len([a for a in model.airplanes if a.state == 'departing'])
                print(f"Krok {step_count}: Samolotów: {len(model.airplanes)} | "
                      f"Oczek.lądow: {waiting_landing}, Lądujące: {landing}, Na stan.: {at_stand}, "
                      f"Oczek.start: {waiting_dep}, Startujące: {departing}")
        
        print(f"\nSymulacja zakończona po {step_count} krokach.")
        
        # Pokazanie końcowych statystyk
        print("Końcowe statystyki:")
        waiting_landing = len([a for a in model.airplanes if a.state == 'waiting_landing'])
        landing = len([a for a in model.airplanes if a.state == 'landing'])
        taxi_to_stand = len([a for a in model.airplanes if a.state == 'taxiing_to_stand'])
        at_stand = len([a for a in model.airplanes if a.state == 'at_stand'])
        taxi_to_rwy = len([a for a in model.airplanes if a.state == 'taxiing_to_runway'])
        waiting_dep = len([a for a in model.airplanes if a.state == 'waiting_departure'])
        departing = len([a for a in model.airplanes if a.state == 'departing'])
        
        print(f"- Kierunek wiatru: RWY {model.wind_direction}")
        print(f"- Aktywny pas: {model.runway_controller.active_runway}")
        print(f"- Samoloty oczekujące na lądowanie: {waiting_landing}")
        print(f"- Samoloty lądujące: {landing}")
        print(f"- Samoloty taxi do stanowiska: {taxi_to_stand}")
        print(f"- Samoloty na stanowisku: {at_stand}")
        print(f"- Samoloty taxi do pasa: {taxi_to_rwy}")
        print(f"- Samoloty oczekujące na start: {waiting_dep}")
        print(f"- Samoloty startujące: {departing}")
        print(f"- Pas zajęty: {'TAK' if model.runway_controller.is_busy else 'NIE'}")
        print(f"- Kolejka lądowań: {model.runway_controller.get_landing_queue_length()}")
        print(f"- Kolejka startów: {model.runway_controller.get_departure_queue_length()}")
        
        # Pokazanie końcowego stanu
        print("Pokazywanie końcowego stanu...")
        viz.show_static()
        
    else:
        print("Nieprawidłowy wybór. Uruchamianie domyślnej animacji...")
        anim = viz.animate(frames=100, interval=100)
        plt.show()
    
    print("\n✅ Symulacja zakończona!")


def demo_quick():
    """Szybka demonstracja symulacji"""
    print("🚀 Szybka demonstracja symulacji lotniska Balice...")
    
    # Tworzenie modelu
    model = AirportModel(num_arriving_airplanes=3, wind_direction="07", arrival_rate=0.15)
    
    # Tworzenie wizualizacji
    viz = AirportVisualization(model)
    
    # Uruchomienie kilku kroków
    print("Uruchamianie 30 kroków symulacji...")
    for i in range(30):
        model.step()
        waiting_landing = len([a for a in model.airplanes if a.state == 'waiting_landing'])
        landing = len([a for a in model.airplanes if a.state == 'landing'])
        at_stand = len([a for a in model.airplanes if a.state == 'at_stand'])
        waiting_dep = len([a for a in model.airplanes if a.state == 'waiting_departure'])
        print(f"Krok {i+1}: Samolotów: {len(model.airplanes)} | "
              f"Oczek.lądow: {waiting_landing}, Lądujące: {landing}, "
              f"Na stanow.: {at_stand}, Oczek.start: {waiting_dep}")
    
    # Pokazanie końcowego stanu
    viz.show_static()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_quick()
    else:
        main()
