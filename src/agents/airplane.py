import random
import math
from typing import Optional, Dict, Tuple
from mesa import Agent
from src.segment_manager import SegmentManager, ConflictProposal
from src.movement_controller import MovementController, Position


class Airplane(Agent):
    """Agent reprezentujący samolot na płycie lotniska"""
    
    def __init__(self, model, unique_id, airplane_type="arrival"):
        super().__init__(model)
        self.unique_id = unique_id
        self.airplane_type = airplane_type  # "arrival" lub "departure"
        # Stany: waiting_landing, landing, taxiing_to_stand, at_stand, taxiing_to_runway, waiting_departure, departing
        if airplane_type == "arrival":
            self.state = "waiting_landing"
        else:
            self.state = "at_stand"
        
        self.landing_time = 0
        self.max_landing_time = 3  # Kroki potrzebne do wylądowania
        self.taxi_time = 0
        self.stand_time = 0
        self.max_stand_time = 10  # Czas obsługi na stanowisku
        self.departure_time = 0
        self.max_departure_time = 3  # Kroki potrzebne do startu
        self.target_node = None
        self.current_node = None
        self.path = []  # Ścieżka do celu
        self.is_in_queue = False
        
        # System rezerwacji segmentów
        self.reserved_segments = []  # Lista zarezerwowanych segmentów
        self.waiting_for_segment = None  # Segment na który czeka
        self.conflict_proposals_sent = []  # Wysłane propozycje
        self.conflict_proposals_received = []  # Otrzymane propozycje
        self.priority = 1  # Priorytet samolotu (wyższa liczba = wyższy priorytet)
        self.wait_time = 0  # Czas oczekiwania na segment
        self.max_wait_time = 5  # Maksymalny czas oczekiwania przed prośbą o arbitraż
        
        # System płynnego ruchu
        self.position = Position(0.0, 0.0)  # Aktualna pozycja z interpolacją
        self.movement_controller = MovementController()
        self.movement_start_time = 0  # Kiedy rozpoczął ruch między węzłami
        self.movement_duration = 1  # Ile ticków zajmuje przejście
        self.is_moving = False  # Czy aktualnie się porusza między węzłami
        
        # System kolejek na drogach
        self.blocked_by_airplane = None  # ID samolotu który blokuje drogę
        self.waiting_position = None  # Pozycja gdzie czeka
        self.queue_position = 0  # Pozycja w kolejce (0 = pierwszy)
        
    def step(self):
        """Główna logika samolotu na płycie lotniska"""
        if self.state == "waiting_landing":
            self.wait_for_landing()
        elif self.state == "landing":
            self.land()
        elif self.state == "taxiing_to_stand":
            self.taxi_to_stand()
        elif self.state == "at_stand":
            self.at_stand_service()
        elif self.state == "taxiing_to_runway":
            self.taxi_to_runway()
        elif self.state == "waiting_departure":
            self.wait_for_departure()
        elif self.state == "departing":
            self.depart()
    
    def wait_for_landing(self):
        """Oczekiwanie na pozwolenie na lądowanie"""
        if not self.is_in_queue:
            # Dodaj samolot do kolejki lądowania
            self.model.runway_controller.add_to_landing_queue(self)
            self.is_in_queue = True
    
    def land(self):
        """Proces lądowania - samolot zatrzymuje się na pasie"""
        self.landing_time += 1
        
        if self.landing_time >= self.max_landing_time:
            self.state = "taxiing_to_stand"
            self.landing_time = 0
            self.model.runway_controller.finish_landing()
            
            # Wybierz wolne stanowisko postojowe
            self.choose_stand()
    
    def choose_stand(self):
        """Wybór wolnego stanowiska postojowego"""
        stand_nodes = self.model.graph.get_stand_nodes()
        occupied_stands = [a.current_node for a in self.model.airplanes 
                          if a != self and a.state == "at_stand"]
        
        available_stands = [s for s in stand_nodes if s not in occupied_stands]
        
        if available_stands:
            self.target_node = self.random.choice(available_stands)
        elif stand_nodes:
            # Jeśli wszystkie zajęte, wybierz losowe
            self.target_node = self.random.choice(stand_nodes)
        else:
            # Jeśli nie ma stanowisk, użyj apron
            apron_nodes = self.model.graph.get_apron_nodes()
            if apron_nodes:
                self.target_node = self.random.choice(apron_nodes)
        
        # Znajdź ścieżkę do stanowiska
        if self.target_node and self.current_node:
            self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
            if len(self.path) > 1:
                self.path.pop(0)  # Usuń obecny węzeł z ścieżki
    
    def taxi_to_stand(self):
        """Taxi do stanowiska postojowego"""
        self._move_along_path()
        
        # Sprawdź czy dotarł do stanowiska
        if self.current_node == self.target_node:
            self.state = "at_stand"
            self.stand_time = 0
    
    def at_stand_service(self):
        """Obsługa na stanowisku postojowym"""
        self.stand_time += 1
        
        if self.stand_time >= self.max_stand_time:
            # Koniec obsługi, przygotuj się do odlotu
            self.state = "taxiing_to_runway"
            self.target_node = self.model.runway_controller.get_active_runway()
            
            # Znajdź ścieżkę do pasa startowego
            if self.target_node and self.current_node:
                self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
                if len(self.path) > 1:
                    self.path.pop(0)
    
    def taxi_to_runway(self):
        """Taxi do pasa startowego"""
        self._move_along_path()
        
        # Sprawdź czy dotarł do pasa
        if self.current_node == self.target_node:
            self.state = "waiting_departure"
    
    def wait_for_departure(self):
        """Oczekiwanie na pozwolenie na start"""
        if not self.is_in_queue:
            self.model.runway_controller.add_to_departure_queue(self)
            self.is_in_queue = True
    
    def depart(self):
        """Proces startu i odlotu - samolot startuje z pasa"""
        self.departure_time += 1
        
        if self.departure_time >= self.max_departure_time:
            # Samolot odleciał - usuń z symulacji
            self.model.runway_controller.finish_departure()
            if self in self.model.airplanes:
                self.model.airplanes.remove(self)
    
    def _move_along_path(self):
        """Wspólna metoda ruchu po ścieżce z płynnym ruchem i systemem rezerwacji"""
        # Jeśli aktualnie się poruszamy, aktualizuj pozycję
        if self.is_moving:
            self._update_movement()
            return
        
        if not self.path:
            # Jeśli nie ma ścieżki, spróbuj znaleźć nową
            if self.target_node and self.current_node:
                self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
                if len(self.path) > 1:
                    self.path.pop(0)
        
        if self.path:
            next_node = self.path[0]
            
            # Rezerwuj KRAWĘDŹ między current_node a next_node (bez wymijania)
            if self.current_node is None:
                # brak pozycji początkowej -> nie ruszamy
                return
            
            # Oblicz czas ruchu dla tej krawędzi (potrzebujemy duration dla rezerwacji)
            start_pos = self.model.graph.get_node_position(self.current_node)
            target_pos = self.model.graph.get_node_position(next_node)
            if start_pos and target_pos:
                distance = self.movement_controller.calculate_distance(start_pos, target_pos)
                edge_type = self.model.graph.get_edge_type(self.current_node, next_node)
                if edge_type == "runway":
                    movement_type = "landing"
                else:
                    movement_type = self.movement_controller.get_movement_type_for_state(self.state)
                estimated_duration = self.movement_controller.calculate_movement_time(distance, movement_type)
            else:
                estimated_duration = 10  # fallback
            
            success, conflict_airplane = self.model.segment_manager.request_edge_with_no_passing(
                self.current_node, next_node, self.unique_id, estimated_duration, self.model.step_count
            )
            
            if success:
                # Segment zarezerwowany - rozpocznij ruch
                self._start_movement_to_node(next_node)
                self.path.pop(0)
                self.reserved_segments.append(next_node)
                self.wait_time = 0
                self.waiting_for_segment = None
                # Wyczyść stan oczekiwania
                self.blocked_by_airplane = None
                self.waiting_position = None
                self.queue_position = 0
                
                # Zwolnij poprzednią krawędź jeśli istniała
                if len(self.reserved_segments) > 0:
                    # reserved_segments przechowuje węzły docelowe - spróbujemy zwolnić poprzednią krawędź
                    # Poprzednia krawędź: (prev_node, current_node)
                    # Nie zawsze możliwe gdy to pierwszy ruch
                    pass
            else:
                # Konflikt - samolot musi czekać w kolejce (zakaz wymijania)
                self.wait_time += 1
                self.waiting_for_segment = next_node
                self.blocked_by_airplane = conflict_airplane
                
                # Ustaw pozycję oczekiwania jeśli nie jest ustawiona
                if not self.waiting_position:
                    self.waiting_position = self.get_position()
                
                # Sprawdź czy można rozwiązać konflikt przez arbitraż
                if self.wait_time >= self.max_wait_time:
                    self._request_controller_arbitration(next_node, conflict_airplane)
    
    def _start_movement_to_node(self, target_node: int):
        """Rozpoczyna ruch do określonego węzła"""
        if not self.current_node:
            # Jeśli nie ma pozycji startowej, użyj pozycji węzła docelowego
            target_pos = self.model.graph.get_node_position(target_node)
            if target_pos:
                self.position.x, self.position.y = target_pos
                self.current_node = target_node
                return
        
        start_pos = self.model.graph.get_node_position(self.current_node)
        target_pos = self.model.graph.get_node_position(target_node)
        
        if start_pos and target_pos:
            # Oblicz czas ruchu na podstawie odległości i typu ruchu
            distance = self.movement_controller.calculate_distance(start_pos, target_pos)
            # Wybór typu ruchu: jeśli krawędź to runway, użyj prędkości pasa (szybszej)
            edge_type = self.model.graph.get_edge_type(self.current_node, target_node)
            if edge_type == "runway":
                movement_type = "landing"  # Na pasie poruszamy się szybciej
            else:
                movement_type = self.movement_controller.get_movement_type_for_state(self.state)
            self.movement_duration = self.movement_controller.calculate_movement_time(distance, movement_type)
            
            # Ustaw parametry ruchu
            self.movement_start_time = self.model.step_count
            self.is_moving = True
            self.position.current_node = self.current_node
            self.position.target_node = target_node
            self.position.progress = 0.0
    
    def _update_movement(self):
        """Aktualizuje pozycję podczas ruchu między węzłami"""
        if not self.is_moving:
            return
        
        # Oblicz postęp ruchu
        elapsed_time = self.model.step_count - self.movement_start_time
        progress = min(1.0, elapsed_time / self.movement_duration)
        
        # Interpoluj pozycję
        start_pos = self.model.graph.get_node_position(self.position.current_node)
        target_pos = self.model.graph.get_node_position(self.position.target_node)
        
        if start_pos and target_pos:
            self.position.x, self.position.y = self.movement_controller.interpolate_position(
                start_pos, target_pos, progress
            )
            self.position.progress = progress
        
        # Sprawdź czy ruch się zakończył
        if progress >= 1.0:
            self._finish_movement()
    
    def _finish_movement(self):
        """Kończy ruch i aktualizuje pozycję"""
        if self.position.target_node:
            # Zwolnij krawędź i poprzedni węzeł po zakończeniu ruchu
            prev_node = self.current_node
            finished_target = self.position.target_node
            self.current_node = self.position.target_node
            target_pos = self.model.graph.get_node_position(self.position.target_node)
            if target_pos:
                self.position.x, self.position.y = target_pos
            if prev_node is not None:
                # Zwolnij krawędź
                self.model.segment_manager.release_edge(prev_node, finished_target, self.unique_id, self.model.step_count)
                # Zwolnij poprzedni węzeł (teraz jesteśmy już w docelowym)
                self.model.segment_manager.release_node(prev_node, self.unique_id, self.model.step_count)
        
        self.is_moving = False
        self.position.progress = 0.0
        self.position.current_node = self.current_node
        self.position.target_node = None
    
    def _handle_segment_conflict(self, segment_id: int, conflict_airplane_id: int):
        """Obsługuje konflikt dostępu do segmentu"""
        # Sprawdź czy już wysłaliśmy propozycję
        existing_proposal = any(
            p["to_airplane"] == conflict_airplane_id
            for p in self.conflict_proposals_sent
        )
        
        if not existing_proposal:
            # Wyślij propozycję rozwiązania konfliktu
            proposal = self._create_conflict_proposal(segment_id, conflict_airplane_id)
            if proposal:
                proposal["from_airplane"] = self.unique_id
                proposal["to_airplane"] = conflict_airplane_id
                self.conflict_proposals_sent.append(proposal)
                # Dodaj propozycję do segment managera
                self.model.segment_manager.create_conflict_proposal(
                    self.unique_id, conflict_airplane_id, 
                    proposal["type"], proposal["details"], self.model.step_count
                )
        
        # Sprawdź czy czekamy za długo
        if self.wait_time >= self.max_wait_time:
            # Poproś kontrolera o arbitraż
            self._request_controller_arbitration(segment_id, conflict_airplane_id)
    
    def _create_conflict_proposal(self, segment_id: int, conflict_airplane_id: int) -> Optional[Dict]:
        """Tworzy propozycję rozwiązania konfliktu"""
        # Różne strategie w zależności od sytuacji
        if self.state in ["taxiing_to_stand", "taxiing_to_runway"]:
            # Propozycja: poczekaj chwilę
            return {
                "type": "wait",
                "details": {
                    "wait_time": 2,
                    "reason": "taxiing_priority"
                }
            }
        elif self.state == "waiting_departure":
            # Propozycja: alternatywna ścieżka
            return {
                "type": "alternative_route",
                "details": {
                    "reason": "departure_priority"
                }
            }
        else:
            # Propozycja: zamiana priorytetów
            return {
                "type": "priority_swap",
                "details": {
                    "new_priority": self.priority + 1,
                    "reason": "urgent_movement"
                }
            }
    
    def _request_controller_arbitration(self, segment_id: int, conflict_airplane_id: int):
        """Prosi kontrolera o arbitraż konfliktu"""
        winner = self.model.segment_manager.resolve_conflict_by_controller(
            segment_id, self.unique_id, conflict_airplane_id, self.model.step_count
        )
        
        if winner == self.unique_id:
            # Wygrałem - mogę przejść
            self.path.pop(0)
            self.current_node = segment_id
            self.reserved_segments.append(segment_id)
            self.wait_time = 0
            self.waiting_for_segment = None
        else:
            # Przegrałem - muszę znaleźć alternatywną ścieżkę
            self._find_alternative_route()
    
    def _find_alternative_route(self):
        """Znajduje alternatywną ścieżkę gdy nie można przejść przez konfliktowy segment"""
        if self.target_node and self.current_node:
            # Znajdź ścieżkę omijającą konfliktowy segment
            all_paths = self.model.graph.find_all_paths(self.current_node, self.target_node)
            
            for path in all_paths:
                if len(path) > 1 and self.waiting_for_segment not in path[1:]:
                    self.path = path[1:]  # Usuń obecny węzeł
                    self.waiting_for_segment = None
                    self.wait_time = 0
                    break
    
    def process_conflict_proposals(self):
        """Przetwarza otrzymane propozycje konfliktów"""
        proposals = self.model.segment_manager.get_conflict_proposals_for_airplane(self.unique_id)
        
        for proposal in proposals:
            if proposal not in self.conflict_proposals_received:
                self.conflict_proposals_received.append(proposal)
                
                # Sprawdź czy możemy zaakceptować propozycję
                if self._evaluate_proposal(proposal):
                    self._accept_proposal(proposal)
                else:
                    self._reject_proposal(proposal)
    
    def _evaluate_proposal(self, proposal: ConflictProposal) -> bool:
        """Ocenia czy można zaakceptować propozycję"""
        if proposal.proposal_type == "wait":
            # Zaakceptuj jeśli nie jesteśmy w pośpiechu
            return self.state not in ["waiting_departure", "departing"]
        elif proposal.proposal_type == "alternative_route":
            # Zaakceptuj jeśli możemy znaleźć alternatywną ścieżkę
            return self.target_node is not None
        elif proposal.proposal_type == "priority_swap":
            # Zaakceptuj jeśli możemy obniżyć priorytet
            return self.priority > 1
        
        return False
    
    def _accept_proposal(self, proposal: ConflictProposal):
        """Akceptuje propozycję"""
        if proposal.proposal_type == "wait":
            # Poczekaj określony czas
            self.wait_time = proposal.details.get("wait_time", 2)
        elif proposal.proposal_type == "alternative_route":
            # Znajdź alternatywną ścieżkę
            self._find_alternative_route()
        elif proposal.proposal_type == "priority_swap":
            # Obniż priorytet
            self.priority = max(1, self.priority - 1)
    
    def _reject_proposal(self, proposal: ConflictProposal):
        """Odrzuca propozycję"""
        # Propozycja zostaje odrzucona - konflikt będzie rozstrzygnięty przez kontrolera
        pass
    
    def is_node_free(self, node_id):
        """Sprawdza czy węzeł jest wolny"""
        for agent in self.model.airplanes:
            if agent != self and hasattr(agent, 'current_node') and agent.current_node == node_id:
                return False
        return True
    
    def get_position(self):
        """Zwraca pozycję samolotu z interpolacją"""
        return (self.position.x, self.position.y)
    
    def get_color(self):
        """Zwraca kolor dla wizualizacji"""
        if self.state == "waiting_landing":
            return "blue"
        elif self.state == "landing":
            return "red"
        elif self.state == "taxiing_to_stand":
            return "orange"
        elif self.state == "at_stand":
            return "green"
        elif self.state == "taxiing_to_runway":
            return "yellow"
        elif self.state == "waiting_departure":
            return "purple"
        elif self.state == "departing":
            return "magenta"
        else:
            return "gray"
