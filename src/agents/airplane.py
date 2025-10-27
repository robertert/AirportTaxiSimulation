import random
import math
from mesa import Agent


class Airplane(Agent):
    """Agent reprezentujący samolot na płycie lotniska"""
    
    def __init__(self, model, unique_id):
        super().__init__(model)
        self.unique_id = unique_id
        self.state = "waiting"  # waiting, landing, landed, taxiing
        self.landing_time = 0
        self.max_landing_time = 3  # Kroki potrzebne do wylądowania
        self.taxi_time = 0
        self.max_taxi_time = 5  # Kroki potrzebne do taxi
        self.target_node = None
        self.current_node = None
        self.path = []  # Ścieżka do celu
        self.is_in_queue = False
        
    def step(self):
        """Główna logika samolotu na płycie lotniska"""
        if self.state == "waiting":
            self.wait_for_landing()
        elif self.state == "landing":
            self.land()
        elif self.state == "landed":
            self.start_taxi()
        elif self.state == "taxiing":
            self.taxi_to_gate()
    
    def wait_for_landing(self):
        """Oczekiwanie na pozwolenie na lądowanie"""
        if not self.is_in_queue:
            # Dodaj samolot do kolejki lądowania
            self.model.runway_controller.add_to_queue(self)
            self.is_in_queue = True
    
    def land(self):
        """Proces lądowania"""
        self.landing_time += 1
        
        if self.landing_time >= self.max_landing_time:
            self.state = "landed"
            self.model.runway_controller.finish_landing()
    
    def start_taxi(self):
        """Rozpoczęcie taxi do bramki"""
        if self.target_node is None:
            # Wybierz losowy węzeł stanowiska postojowego
            stand_nodes = self.model.graph.get_stand_nodes()
            if stand_nodes:
                self.target_node = self.random.choice(stand_nodes)
            else:
                # Jeśli nie ma stanowisk, wybierz węzeł apron
                apron_nodes = self.model.graph.get_apron_nodes()
                if apron_nodes:
                    self.target_node = self.random.choice(apron_nodes)
        
        # Znajdź ścieżkę do celu
        if self.target_node and self.current_node:
            self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
            if len(self.path) > 1:
                self.path.pop(0)  # Usuń obecny węzeł z ścieżki
        
        self.state = "taxiing"
        self.taxi_time = 0
    
    def taxi_to_gate(self):
        """Ruch taxi do bramki po grafie lotniska"""
        if not self.path:
            # Jeśli nie ma ścieżki, spróbuj znaleźć nową
            if self.target_node and self.current_node:
                self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
                if len(self.path) > 1:
                    self.path.pop(0)
        
        if self.path:
            # Przejdź do następnego węzła w ścieżce
            next_node = self.path.pop(0)
            
            # Sprawdź czy węzeł jest wolny
            if self.is_node_free(next_node):
                self.current_node = next_node
                self.taxi_time += 1
            else:
                # Węzeł zajęty, czekaj
                pass
        
        # Sprawdź czy dotarł do celu
        if self.current_node == self.target_node:
            self.taxi_time += 1
            if self.taxi_time >= self.max_taxi_time:
                # Samolot dotarł do bramki - usunięcie z symulacji
                if self in self.model.airplanes:
                    self.model.airplanes.remove(self)
    
    def is_node_free(self, node_id):
        """Sprawdza czy węzeł jest wolny"""
        for agent in self.model.airplanes:
            if agent != self and hasattr(agent, 'current_node') and agent.current_node == node_id:
                return False
        return True
    
    def get_position(self):
        """Zwraca pozycję samolotu na podstawie węzła"""
        if self.current_node:
            return self.model.graph.get_node_position(self.current_node)
        return (0, 0)
    
    def get_color(self):
        """Zwraca kolor dla wizualizacji"""
        if self.state == "waiting":
            return "blue"
        elif self.state == "landing":
            return "red"
        elif self.state == "landed":
            return "green"
        else:  # taxiing
            return "orange"
