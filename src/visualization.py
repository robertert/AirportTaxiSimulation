import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.patches import Rectangle, Circle
import matplotlib.patches as mpatches
import networkx as nx
from matplotlib.image import imread
import os


class AirportVisualization:
    """Wizualizacja symulacji lotniska z grafem"""
    
    def __init__(self, model):
        self.model = model
        # Zmienione proporcje dla lepszego dopasowania do ekranu
        self.fig, self.ax = plt.subplots(figsize=(12, 16))
        
        # Ładowanie obrazka tła
        self.background_image = None
        self.load_background()
        
        self.setup_plot()
        
    def load_background(self):
        """Ładowanie obrazka tła"""
        try:
            # Sprawdź czy plik istnieje w katalogu głównym projektu
            bg_path = "bg.png"
            if os.path.exists(bg_path):
                self.background_image = imread(bg_path)
                print(f"Załadowano obrazek tła: {bg_path}")
            else:
                print("Nie znaleziono pliku bg.png")
        except Exception as e:
            print(f"Błąd podczas ładowania obrazka tła: {e}")
            self.background_image = None
        
    def setup_plot(self):
        """Konfiguracja wykresu"""
        # Obrócone ustawienia dla siatki 69x36 (szerokość x wysokość)
        self.ax.set_xlim(-2, 71)  # Szerokość siatki + marginesy (obrócone)
        self.ax.set_ylim(-2, 38)  # Wysokość siatki + marginesy (obrócone)
        self.ax.set_aspect('equal')
        self.ax.set_title('Symulacja Lotniska Balice - Siatka 69x36', fontsize=16, fontweight='bold')
        self.ax.set_xlabel('Pozycja X (siatka)', fontsize=12)
        self.ax.set_ylabel('Pozycja Y (siatka)', fontsize=12)
        
        # Wyświetlanie obrazka tła
        self.draw_background()
        
        # Rysowanie grafu lotniska
        self.draw_airport_graph()
        
        # Legenda - zaktualizowana dla siatki
        legend_elements = [
            mpatches.Patch(color='blue', label='Oczekujące na lądowanie'),
            mpatches.Patch(color='red', label='Lądujące'),
            mpatches.Patch(color='green', label='Wylądowane'),
            mpatches.Patch(color='orange', label='Taxi do bramki'),
            mpatches.Patch(color='#2c2c2c', label='Pas startowy'),
            mpatches.Patch(color='#32CD32', label='Stanowiska'),
            mpatches.Patch(color='#4169E1', label='Apron'),
            mpatches.Patch(color='#808080', label='Taxiway'),
            mpatches.Patch(color='#FF8C00', label='Łączniki')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
        
        # Siatka pomocnicza dla lepszej orientacji
        self.ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # Dodanie linii pomocniczych co 5 jednostek (obrócone)
        for i in range(0, 75, 5):
            self.ax.axvline(x=i, color='lightgray', linestyle='--', alpha=0.2, linewidth=0.5)
        for i in range(0, 40, 5):
            self.ax.axhline(y=i, color='lightgray', linestyle='--', alpha=0.2, linewidth=0.5)
    
    def draw_background(self):
        """Rysowanie obrazka tła"""
        if self.background_image is not None:
            try:
                # Obróć obrazek o 90 stopni w lewo (3 obroty o 90 stopni w prawo)
                rotated_image = np.rot90(self.background_image, k=1)
                
                # Wyświetl obrócony obrazek tła na całym obszarze wykresu
                self.ax.imshow(rotated_image, 
                             extent=[0, 69, 0, 36],  # [left, right, bottom, top]
                             aspect='auto', 
                             alpha=0.3,  # Przezroczystość
                             zorder=0)  # Najniższa warstwa
            except Exception as e:
                print(f"Błąd podczas wyświetlania obrazka tła: {e}")
        
    def draw_airport_graph(self):
        """Rysowanie grafu lotniska"""
        # Kolory dla różnych typów węzłów - bardziej wyraziste dla siatki
        node_colors = {
            "runway_thr": "#2c2c2c",  # runway (bardzo ciemnoszary)
            "taxiway": "#808080",      # taxiway (szary)
            "apron": "#4169E1",        # apron (królewski niebieski)
            "stand": "#32CD32",        # stanowiska (zielony)
            "connector": "#FF8C00",    # łączniki (ciemny pomarańczowy)
        }
        
        # Rysowanie krawędzi
        for edge in self.model.graph.graph.edges(data=True):
            from_node = self.model.graph.get_node_position(edge[0])
            to_node = self.model.graph.get_node_position(edge[1])
            
            if from_node and to_node:
                # Różne grubości linii dla różnych typów krawędzi
                edge_type = edge[2].get('type', 'taxi')
                if edge_type == 'runway':
                    linewidth = 4
                    color = '#2c2c2c'
                elif edge_type == 'taxiway':
                    linewidth = 2
                    color = '#808080'
                elif edge_type == 'stand_link':
                    linewidth = 1
                    color = '#32CD32'
                elif edge_type == 'apron_link':
                    linewidth = 1.5
                    color = '#4169E1'
                else:
                    linewidth = 1
                    color = '#FF8C00'
                
                self.ax.plot([from_node[0], to_node[0]], [from_node[1], to_node[1]], 
                           color=color, alpha=0.8, linewidth=linewidth)
        
        # Rysowanie węzłów
        for node_id, data in self.model.graph.graph.nodes(data=True):
            x, y = data['x'], data['y']
            node_type = data['type']
            color = node_colors.get(node_type, "#ffffff")
            
            # Różne rozmiary dla różnych typów węzłów - dostosowane do siatki
            if node_type == "runway_thr":
                size = 150
                marker = 's'  # kwadrat
            elif node_type == "stand":
                size = 100
                marker = 'o'  # koło
            elif node_type == "apron":
                size = 120
                marker = 'D'  # diament
            elif node_type == "taxiway":
                size = 80
                marker = '^'  # trójkąt
            else:  # connector
                size = 60
                marker = 'o'  # koło
            
            self.ax.scatter(x, y, c=color, s=size, marker=marker, 
                          edgecolors='black', linewidth=1, alpha=0.8, zorder=2)
            
            # Etykiety węzłów - mniejsze dla siatki
            
    def render(self):
        """Renderowanie aktualnego stanu symulacji"""
        self.ax.clear()
        self.setup_plot()
        
        # Wyświetlanie obrazka tła ponownie
        self.draw_background()
        
        # Rysowanie samolotów
        for airplane in self.model.airplanes:
            if hasattr(airplane, 'get_position'):
                x, y = airplane.get_position()
            elif hasattr(airplane, 'current_node') and airplane.current_node:
                pos = self.model.graph.get_node_position(airplane.current_node)
                if pos:
                    x, y = pos
                else:
                    continue
            else:
                continue
                
            color = airplane.get_color()
            size = 80 if airplane.state == "landing" else 60  # Mniejsze samoloty dla siatki
            
            # Różne kształty dla różnych stanów
            if airplane.state == "waiting":
                marker = '^'  # Trójkąt
            elif airplane.state == "landing":
                marker = 'o'  # Koło
            elif airplane.state == "landed":
                marker = 'D'  # Diament
            else:  # taxiing
                marker = 's'  # Kwadrat
            
            self.ax.scatter(x, y, c=color, s=size, marker=marker, 
                          edgecolors='black', linewidth=2, alpha=0.9, zorder=5)
            
            # Etykieta z ID samolotu - mniejsza dla siatki
            self.ax.annotate(f'A{airplane.unique_id}', (x, y), 
                           xytext=(0, -20), textcoords='offset points',
                           fontsize=8, fontweight='bold', ha='center', zorder=6)
        
        # Informacje o stanie
        info_text = f"Krok: {len(self.model.airplanes) if hasattr(self.model, 'airplanes') else 0}\n"
        waiting = len([a for a in self.model.airplanes if a.state == 'waiting'])
        landing = len([a for a in self.model.airplanes if a.state == 'landing'])
        landed = len([a for a in self.model.airplanes if a.state == 'landed'])
        taxiing = len([a for a in self.model.airplanes if a.state == 'taxiing'])
        info_text += f"Oczekujące: {waiting}\n"
        info_text += f"Lądujące: {landing}\n"
        info_text += f"Wylądowane: {landed}\n"
        info_text += f"Taxi: {taxiing}\n"
        info_text += f"Pas zajęty: {'TAK' if self.model.runway_controller.is_busy else 'NIE'}\n"
        info_text += f"Kolejka: {self.model.runway_controller.get_queue_length()}"
        
        self.ax.text(0.02, 0.98, info_text, transform=self.ax.transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.9), zorder=10)
        
        plt.tight_layout()
    
    def animate(self, frames=100, interval=500):
        """Animacja symulacji"""
        def animate_frame(frame):
            if self.model.running:
                self.model.step()
            self.render()
            return []
        
        anim = animation.FuncAnimation(self.fig, animate_frame, frames=frames, 
                                     interval=interval, blit=False, repeat=False)
        return anim
    
    def show_static(self):
        """Pokazanie statycznego obrazu"""
        self.render()
        plt.show()
    
    def save_animation(self, filename="airport_simulation.gif", frames=100, interval=500):
        """Zapisanie animacji do pliku"""
        anim = self.animate(frames=frames, interval=interval)
        anim.save(filename, writer='pillow', fps=2)
        print(f"Animacja zapisana jako {filename}")

