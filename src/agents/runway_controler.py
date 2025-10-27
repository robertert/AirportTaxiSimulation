import random
import math
from mesa import Agent

class RunwayController(Agent):
    """Agent kontrolujący pas startowy i kolejkę lądowania"""
    
    def __init__(self, model, unique_id):
        super().__init__(model)
        self.unique_id = unique_id
        self.is_busy = False
        self.current_airplane = None
        self.landing_queue = []  # Kolejka samolotów oczekujących na lądowanie
        self.runway_node = None  # Węzeł pasa startowego
    
    def step(self):
        """Logika kontrolera pasa startowego"""
        # Znajdź węzeł pasa startowego jeśli jeszcze nie został wybrany
        if self.runway_node is None:
            runway_nodes = self.model.graph.get_runway_nodes()
            if runway_nodes:
                self.runway_node = runway_nodes[0]  # Użyj pierwszego pasa startowego
        
        # Jeśli pas jest wolny i są samoloty w kolejce
        if not self.is_busy and self.landing_queue and self.runway_node:
            airplane = self.landing_queue.pop(0)
            self.is_busy = True
            self.current_airplane = airplane
            airplane.state = "landing"
            airplane.landing_time = 0
            # Umieść samolot na węźle pasa startowego
            airplane.current_node = self.runway_node
    
    def add_to_queue(self, airplane):
        """Dodaj samolot do kolejki lądowania"""
        if airplane not in self.landing_queue:
            self.landing_queue.append(airplane)
    
    def finish_landing(self):
        """Zakończenie lądowania"""
        if self.current_airplane:
            self.current_airplane.state = "landed"
        self.is_busy = False
        self.current_airplane = None
    
    def get_queue_length(self):
        """Zwraca długość kolejki"""
        return len(self.landing_queue)
    
    def get_queue_info(self):
        """Zwraca informacje o kolejce"""
        return [f"A{plane.unique_id}" for plane in self.landing_queue]