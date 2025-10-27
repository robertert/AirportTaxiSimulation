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


def main():
    """Główna funkcja uruchamiająca symulację"""
    print("🛫 Uruchamianie symulacji lotniska Balice...")
    print("=" * 50)
    
    # Parametry symulacji
    num_airplanes = 8
    
    print(f"Parametry symulacji:")
    print(f"- Mapa: Graf lotniska (nodes.csv, edges.csv)")
    print(f"- Liczba samolotów: {num_airplanes}")
    print()
    
    # Tworzenie modelu
    model = AirportModel(num_airplanes=num_airplanes)
    
    # Tworzenie wizualizacji
    viz = AirportVisualization(model)
    
    print("Wybierz tryb uruchomienia:")
    print("1. Animacja interaktywna")
    print("2. Statyczny obraz")
    print("3. Zapisz animację do pliku")
    print("4. Uruchom pełną symulację i pokaż statystyki")
    
    choice = input("Twój wybór (1-4): ").strip()
    
    if choice == "1":
        print("Uruchamianie animacji interaktywnej...")
        print("Zamknij okno aby zakończyć.")
        anim = viz.animate(frames=200, interval=500)
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
                waiting = len([a for a in model.airplanes if a.state == 'waiting'])
                landing = len([a for a in model.airplanes if a.state == 'landing'])
                landed = len([a for a in model.airplanes if a.state == 'landed'])
                taxiing = len([a for a in model.airplanes if a.state == 'taxiing'])
                print(f"Krok {step_count}: Oczekujące: {waiting}, Lądujące: {landing}, Wylądowane: {landed}, Taxi: {taxiing}")
        
        print(f"\nSymulacja zakończona po {step_count} krokach.")
        
        # Pokazanie końcowych statystyk
        print("Końcowe statystyki:")
        waiting = len([a for a in model.airplanes if a.state == 'waiting'])
        landing = len([a for a in model.airplanes if a.state == 'landing'])
        landed = len([a for a in model.airplanes if a.state == 'landed'])
        taxiing = len([a for a in model.airplanes if a.state == 'taxiing'])
        print(f"- Samoloty oczekujące: {waiting}")
        print(f"- Samoloty lądujące: {landing}")
        print(f"- Samoloty wylądowane: {landed}")
        print(f"- Samoloty w taxi: {taxiing}")
        print(f"- Pas zajęty: {'TAK' if model.runway_controller.is_busy else 'NIE'}")
        print(f"- Długość kolejki: {model.runway_controller.get_queue_length()}")
        
        # Pokazanie końcowego stanu
        print("Pokazywanie końcowego stanu...")
        viz.show_static()
        
    else:
        print("Nieprawidłowy wybór. Uruchamianie domyślnej animacji...")
        anim = viz.animate(frames=100, interval=500)
        plt.show()
    
    print("\n✅ Symulacja zakończona!")


def demo_quick():
    """Szybka demonstracja symulacji"""
    print("🚀 Szybka demonstracja symulacji lotniska Balice...")
    
    # Tworzenie modelu
    model = AirportModel(num_airplanes=5)
    
    # Tworzenie wizualizacji
    viz = AirportVisualization(model)
    
    # Uruchomienie kilku kroków
    print("Uruchamianie 20 kroków symulacji...")
    for i in range(20):
        model.step()
        waiting = len([a for a in model.airplanes if a.state == 'waiting'])
        landing = len([a for a in model.airplanes if a.state == 'landing'])
        landed = len([a for a in model.airplanes if a.state == 'landed'])
        taxiing = len([a for a in model.airplanes if a.state == 'taxiing'])
        print(f"Krok {i+1}: Oczekujące: {waiting}, Lądujące: {landing}, Wylądowane: {landed}, Taxi: {taxiing}")
    
    # Pokazanie końcowego stanu
    viz.show_static()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_quick()
    else:
        main()
