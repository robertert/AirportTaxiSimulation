from src.graph import AirportGraph
from src.agents.airplane import Airplane
from src.agents.runway_controler import RunwayController
from src.segment_manager import SegmentManager
from mesa import Model
from mesa import DataCollector
import numpy as np
import os

DEFAULTS = {
    'taxi_speed_straight_kts': 20,
    'taxi_speed_turn_kts': 10,
    'min_headway_m': 100,
    'pushback_time_s': 90,
    'runway_lineup_block_s': 20,
    'takeoff_roll_time_s': 35,
    'landing_roll_time_s': 40,
    'runway_buffer_after_exit_s': 15,
    'sep_TT_s': 60,
    'sep_LL_s': 70,
    'sep_TL_s': 90,
    'sep_LT_s': 90,
}

class AirportModel(Model):
    def __init__(self, num_arriving_airplanes=5, wind_direction="07", 
                 arrival_rate=0.1, nodes_file="nodes.csv", edges_file="edges.csv"):
        super().__init__()
        
        # Inicjalizacja grafu lotniska
        self.graph = AirportGraph(nodes_file, edges_file)
        
        # Pobieranie granic grafu dla wizualizacji
        min_x, max_x, min_y, max_y = self.graph.get_graph_bounds()
        self.width = max_x - min_x + 100  # dodajemy margines
        self.height = max_y - min_y + 100
        
        self.num_arriving_airplanes = num_arriving_airplanes
        self.arrival_rate = arrival_rate  # Prawdopodobieństwo pojawienia się nowego samolotu
        self.wind_direction = wind_direction  # Kierunek wiatru "07" lub "25"
        self.defaults = DEFAULTS
        
        # Segment manager do zarządzania rezerwacjami
        self.segment_manager = SegmentManager(self)  # Przekaż referencję do modelu

        # Runway controller z kierunkiem wiatru
        self.runway_controller = RunwayController(self, 1, wind_direction=wind_direction)

        # Lista samolotów w symulacji
        self.airplanes = []
        self.next_airplane_id = 2  # Zaczynamy od 2 (1 jest dla kontrolera)
        
        self.running = True
        self.step_count = 0
        
        # Tworzenie początkowych samolotów przybywających
        self.create_initial_arrivals()


        # LISTA NA CZASY OBSŁUGI (dla samolotów, które już odleciały)
        self.completed_flight_times = []

        self.datacollector = DataCollector(
            model_reporters={
                # Obliczamy średnią z listy completed_flight_times
                "Avg_Service_Time": lambda m: np.mean(m.completed_flight_times) if m.completed_flight_times else 0
            }
        )

    def create_initial_arrivals(self):
        """Tworzy początkowe samoloty przybywające do lądowania"""
        for i in range(self.num_arriving_airplanes):
            airplane = Airplane(self, self.next_airplane_id, airplane_type="arrival")
            # Samoloty przybywające nie mają jeszcze pozycji (są w powietrzu)
            airplane.current_node = None
            self.airplanes.append(airplane)
            self.next_airplane_id += 1
    
    def spawn_new_arrival(self):
        """Spawuje nowy samolot przybywający"""
        if self.random.random() < self.arrival_rate:
            airplane = Airplane(self, self.next_airplane_id, airplane_type="arrival")
            airplane.current_node = None
            self.airplanes.append(airplane)
            self.next_airplane_id += 1

    def log_airplanes_status(self):
        """Loguje stan wszystkich samolotów"""
        print(f"\n{'='*80}")
        print(f"KROK {self.step_count} - Stan samolotów")
        print(f"{'='*80}")
        print(f"Liczba samolotów: {len(self.airplanes)}")
        print(f"Kolejka pasa: {self.runway_controller.get_runway_queue_length()}")
        print(f"Pas zajęty: {'TAK' if self.runway_controller.is_busy else 'NIE'}")
        if self.runway_controller.current_airplane:
            print(f"Aktualna operacja: {self.runway_controller.current_operation} - Samolot {self.runway_controller.current_airplane.unique_id}")
        
        # Statystyki stanów
        states_count = {}
        for airplane in self.airplanes:
            state = airplane.state
            states_count[state] = states_count.get(state, 0) + 1
        print(f"Stany: {', '.join([f'{k}: {v}' for k, v in sorted(states_count.items())])}")
        
        print(f"\n{'ID':<6} {'Typ':<10} {'Stan':<20} {'Węzeł':<8} {'Cel':<8} {'Ścieżka':<8} {'Blokady':<8} {'Kolejka':<8} {'Czeka':<8}")
        print(f"{'-'*80}")
        
        for airplane in sorted(self.airplanes, key=lambda a: a.unique_id):
            node_str = str(airplane.current_node) if airplane.current_node is not None else "None"
            target_str = str(airplane.target_node) if airplane.target_node is not None else "None"
            path_len = len(airplane.path) if airplane.path else 0
            blocked_count = len(airplane.blocked_edges) if hasattr(airplane, 'blocked_edges') else 0
            in_queue = "TAK" if airplane.is_in_queue else "NIE"
            wait_time = airplane.wait_time if hasattr(airplane, 'wait_time') else 0
            
            print(f"{airplane.unique_id:<6} {airplane.airplane_type:<10} {airplane.state:<20} {node_str:<8} {target_str:<8} {path_len:<8} {blocked_count:<8} {in_queue:<8} {wait_time:<8}")
        
        print(f"{'='*80}\n")

    def step(self):
        """Krok symulacji"""
        self.step_count += 1
        print(self.segment_manager.airport_queue)
        # Czasami spawuj nowe samoloty
        self.spawn_new_arrival()
        # Wyczyść stare rezerwacje
        self.segment_manager.cleanup_old_reservations(self.step_count)
        # Krok dla wszystkich agentów
        # Najpierw runway controller
        self.runway_controller.step()
        
        # Potem wszystkie samoloty (kopiujemy listę, bo może się zmienić)
        for airplane in self.airplanes[:]:
            airplane.step()
        
        # Loguj stan wszystkich samolotów
        #self.log_airplanes_status()

        # Zbieraj dane
        self.datacollector.collect(self)


    def portray_cell(cell_type):
        colors = {
            "R": "#7f7f7f",  # runway (ciemnoszary)
            "T": "#bfbfbf",  # taxiway
            "A": "#9999ff",  # apron
            "M": "#66cc66",  # terminal
            "G": "#aaffaa",  # grass
        }
        return {"Shape": "rect", "Color": colors[cell_type], "Filled": True, "Layer": 0}