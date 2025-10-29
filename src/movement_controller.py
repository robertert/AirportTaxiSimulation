import math
from typing import Tuple, Optional, Dict
from dataclasses import dataclass

@dataclass
class Position:
    """Pozycja samolotu z interpolacją między węzłami"""
    x: float
    y: float
    current_node: Optional[int] = None
    target_node: Optional[int] = None
    progress: float = 0.0  # 0.0 = na początku, 1.0 = na końcu ścieżki

class MovementController:
    """Kontroler ruchu samolotów z prędkością i interpolacją"""
    
    def __init__(self):
        # Prędkości w jednostkach na tick (dostosowane do skali lotniska)
        self.speeds = {
            "taxiing": 0.5,      # Wolny ruch taxi
            "landing": 4.0,      # Szybki ruch podczas lądowania
            "departing":4.0,    # Szybki ruch podczas startu
            "holding": 0.0,      # Bez ruchu podczas oczekiwania
            "at_stand": 0.0      # Bez ruchu na stanowisku
        }
        
        # Minimalne czasy przejścia między węzłami (w tickach)
        self.min_transit_times = {
            "taxiing": 2,
            "landing": 1,
            "departing": 1,
            "holding": 1,
            "at_stand": 1
        }
    
    def calculate_movement_time(self, distance: float, movement_type: str) -> int:
        """Oblicza czas potrzebny na przejście między węzłami"""
        speed = self.speeds.get(movement_type, 0.5)
        min_time = self.min_transit_times.get(movement_type, 1)
        
        # Czas oparty na prędkości i odległości
        calculated_time = max(1, int(distance / speed))
        
        # Zawsze minimum określony czas
        return max(calculated_time, min_time)
    
    def interpolate_position(self, start_pos: Tuple[float, float], 
                           end_pos: Tuple[float, float], 
                           progress: float) -> Tuple[float, float]:
        """Interpoluje pozycję między dwoma punktami"""
        if progress <= 0.0:
            return start_pos
        elif progress >= 1.0:
            return end_pos
        
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        
        return (x, y)
    
    def calculate_distance(self, pos1: Tuple[float, float], 
                          pos2: Tuple[float, float]) -> float:
        """Oblicza odległość euklidesową między dwoma pozycjami"""
        return math.sqrt((pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
    
    def get_movement_type_for_state(self, state: str) -> str:
        """Zwraca typ ruchu na podstawie stanu samolotu"""
        if state in ["taxiing_to_stand", "taxiing_to_runway"]:
            return "taxiing"
        elif state == "landing":
            return "landing"
        elif state == "departing":
            return "departing"
        elif state in ["waiting_landing", "waiting_departure"]:
            return "holding"
        elif state == "at_stand":
            return "at_stand"
        else:
            return "taxiing"  # Domyślny typ ruchu
