from src.graph import AirportGraph
from src.agents.airplane import Airplane
from src.agents.runway_controler import RunwayController
from mesa import Model
import os

class AirportModel(Model):
    def __init__(self, num_airplanes, nodes_file="nodes.csv", edges_file="edges.csv"):
        super().__init__()
        
        # Inicjalizacja grafu lotniska
        self.graph = AirportGraph(nodes_file, edges_file)
        
        # Pobieranie granic grafu dla wizualizacji
        min_x, max_x, min_y, max_y = self.graph.get_graph_bounds()
        self.width = max_x - min_x + 100  # dodajemy margines
        self.height = max_y - min_y + 100
        
        self.num_airplanes = num_airplanes
        
        # Runway controller
        self.runway_controller = RunwayController(self, 1)

        # Tworzenie samolotów w węzłach stanowisk postojowych
        self.airplanes = []
        self.create_airplanes()

        self.running = True

    def create_airplanes(self):
        # Pobieramy węzły stanowisk postojowych
        stand_nodes = self.graph.get_stand_nodes()
        
        if not stand_nodes:
            # Jeśli nie ma stanowisk, używamy węzłów apron
            stand_nodes = self.graph.get_apron_nodes()
        
        if not stand_nodes:
            # Jeśli nie ma ani stanowisk ani apron, używamy wszystkich węzłów
            stand_nodes = self.graph.get_all_nodes()
        
        for i in range(self.num_airplanes):
            # Wybieramy losowy węzeł stanowiska
            if stand_nodes:
                node_id = self.random.choice(stand_nodes)
                airplane = Airplane(self, i + 2)
                airplane.current_node = node_id
                airplane.state = "waiting"
                self.airplanes.append(airplane)

    def step(self):
        for agent in self.airplanes + [self.runway_controller]:
            agent.step()


    def portray_cell(cell_type):
        colors = {
            "R": "#7f7f7f",  # runway (ciemnoszary)
            "T": "#bfbfbf",  # taxiway
            "A": "#9999ff",  # apron
            "M": "#66cc66",  # terminal
            "G": "#aaffaa",  # grass
        }
        return {"Shape": "rect", "Color": colors[cell_type], "Filled": True, "Layer": 0}