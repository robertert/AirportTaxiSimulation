from typing import Optional
from mesa import Agent
from src.movement_controller import MovementController, Position


class Airplane(Agent):
    """Agent reprezentujący samolot na płycie lotniska"""
    
    def __init__(self, model, unique_id, airplane_type="arrival"):
        super().__init__(model)
        self.unique_id = unique_id
        self.airplane_type = airplane_type  # "arrival" lub "departure"
        # Stany: waiting_landing, landing, taxiing_to_stand, at_stand,
        #        pushback_pending, pushback, taxiing_to_runway, waiting_departure, departing
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
        self.blocked_edges = []  # Lista zarezerwowanych segmentów
        
        self.priority = 1  # Priorytet samolotu (wyższa liczba = wyższy priorytet)
        self.wait_time = 0  # Czas oczekiwania na segment
        self.max_wait_time = 5  # Maksymalny czas oczekiwania przed prośbą o arbitraż
        self.hold_progress_limit = None  # Limit postępu do zatrzymania się przed segmentem
        
        # System płynnego ruchu
        self.position = Position(0.0, 0.0)  # Aktualna pozycja z interpolacją
        self.movement_controller = MovementController()
        self.movement_start_time = 0  # Kiedy rozpoczął ruch między węzłami
        self.movement_duration = 1  # Ile ticków zajmuje przejście
        self.is_moving = False  # Czy aktualnie się porusza między węzłami
        # Pushback
        self.pushback_started_at: Optional[int] = None
        self.runway_entry_node: Optional[int] = None
        self.departure_hold_node: Optional[int] = None
        
    def step(self):
        """Główna logika samolotu na płycie lotniska"""
        if self.state == "waiting_landing":
            self.wait_for_landing()
        elif self.state == "landing":
            self.land()
        elif self.state == "taxiing_to_exit":
            self.taxi_to_exit()
        elif self.state == "at_exit":
            self.wait_for_stand()
        elif self.state == "taxiing_to_stand":
            self.taxi_to_stand()
        elif self.state == "at_stand":
            self.at_stand_service()
        elif self.state == "pushback_pending":
            self.handle_pushback_pending()
        elif self.state == "pushback":
            self.handle_pushback()
        elif self.state == "waiting_departure":
            self.wait_for_departure()
        elif self.state == "departing":
            self.depart()
    
    def wait_for_landing(self):
        """Oczekiwanie na pozwolenie na lądowanie"""
        if not self.is_in_queue:
            self.model.runway_controller.add_to_runway_queue(self)
            self.is_in_queue = True
    
    def land(self):
        """Proces lądowania - samolot porusza się po pasie"""
        # Poruszaj się po pasie podczas lądowania
        self._move_along_path()
        
        self.landing_time += 1
        
        if self.landing_time >= self.max_landing_time:
            self.state = "taxiing_to_exit"
            self.landing_time = 0
            self.model.runway_controller.finish_landing()

    def choose_exit(self):
        """Wybór wyjścia z pasa startowego"""
        success, blocked_edges = self.model.segment_manager.request_airport_section("taxiway_outbound", self.unique_id)         
        if success:
            self.target_node = blocked_edges[0]['to']
            self.path = self.model.graph.find_shortest_path(self.model.runway_controller.get_runway_entry_node(), blocked_edges[0]['to'])
            if len(self.path) > 1:
                self.path.pop(0)
            return True
        else:
            self.model.segment_manager.release_edges(blocked_edges, self.unique_id)
            self.blocked_edges = []
            return False

    def taxi_to_exit(self):
        """Taxi do wyjścia z pasa startowego"""
        self._move_along_path()
        if self.current_node == self.target_node:
            self.model.segment_manager.release_edges(self.blocked_edges, self.unique_id)
            self.blocked_edges = []
            self.state = "at_exit"
            self.target_node = None
            self.path = []
    
    def wait_for_stand(self):
        """Oczekiwanie na wolne stanowisko postojowe"""
        success_taxiway, blocked_edges_taxiway = self.model.segment_manager.request_airport_section("taxiway", self.unique_id)
        success_apron, blocked_edges_apron = self.model.segment_manager.request_airport_section("apron", self.unique_id)
        if success_taxiway and success_apron and self.choose_stand():
            blocked_edges = blocked_edges_taxiway + blocked_edges_apron
            self.blocked_edges = blocked_edges
            self.state = "taxiing_to_stand"
        else:
            self.model.segment_manager.release_edges(blocked_edges_taxiway, self.unique_id)
            self.model.segment_manager.release_edges(blocked_edges_apron, self.unique_id)
            self.blocked_edges = []
            return

    
    def choose_stand(self):
        """Wybór wolnego stanowiska postojowego"""
        stand_nodes = self.model.graph.get_stand_nodes()
        occupied_stands = [a.current_node for a in self.model.airplanes 
                          if a != self and a.state == "at_stand"]
        
        available_stands = [s for s in stand_nodes if s not in occupied_stands]
        
        if available_stands:
            self.target_node = self.random.choice(available_stands)
            
        else:
            return
        # Znajdź ścieżkę do stanowiska
        if self.target_node and self.current_node:
            self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
            if len(self.path) > 1:
                self.path.pop(0)  # Usuń obecny węzeł z ścieżki
            return True
        else:
            return False
    
    def taxi_to_stand(self):
        """Taxi do stanowiska postojowego"""
        self._move_along_path()
        
        # Sprawdź czy dotarł do stanowiska
        if self.current_node == self.target_node:
            self.model.segment_manager.release_edges(self.blocked_edges, self.unique_id)
            self.blocked_edges = []
            self.state = "at_stand"
            self.stand_time = 0
    
    def at_stand_service(self):
        """Obsługa na stanowisku postojowym"""
        self.stand_time += 1
        
        if self.stand_time >= self.max_stand_time:
            # Koniec obsługi, przygotuj się do odlotu
            self.state = "pushback_pending"
            self.runway_entry_node = self.model.runway_controller.get_runway_entry_node()
            self.departure_hold_node = None
            self.target_node = None
            self.path = []
    
    def handle_pushback_pending(self):
        """Czeka na dostępność tuga/apron i rozpoczyna pushback."""
        now = self.model.step_count
        granted_apron, blocked_edges_apron = self.model.segment_manager.request_airport_section("apron", self.unique_id)
        granted_taxiway, blocked_edges_taxiway = self.model.segment_manager.request_airport_section("taxiway", self.unique_id)
        granted_runway_entry,blocked_edges_runway_entry = self.choose_runway_entry()
        if granted_apron and granted_taxiway and granted_runway_entry:
            blocked_edges = blocked_edges_apron + blocked_edges_taxiway + blocked_edges_runway_entry
            self.blocked_edges = blocked_edges
            self.state = "pushback"
            self.airplane_type = "departure"
            self.pushback_started_at = now
        else:
            self.model.segment_manager.release_edges(blocked_edges_apron, self.unique_id)
            self.model.segment_manager.release_edges(blocked_edges_taxiway, self.unique_id)
            self.model.segment_manager.release_edges(blocked_edges_runway_entry, self.unique_id)
            self.blocked_edges = []
    
    def choose_runway_entry(self):
        """Wybór węzła wejścia na pas startowy"""
        runway_entry_edges = self.model.graph.get_edges_by_type("runway_entry")
        blocked_edges = []
        for edge in runway_entry_edges:
            if edge['to'] == self.runway_entry_node or edge['from'] == self.runway_entry_node:
                granted = self.model.segment_manager.request_edge(edge['from'], edge['to'], self.unique_id)
                if granted:
                    self.target_node = edge['from']
                    self.path = self.model.graph.find_shortest_path(self.current_node, edge['to'])
                    if len(self.path) > 1:
                        self.path.pop(0)
                    blocked_edges.append(edge)
                    return True, blocked_edges
                else:
                    return False, blocked_edges
        return False, blocked_edges



    def handle_pushback(self):
        """Obsługa trwającego pushbacku; po zakończeniu przejście do taxi_to_runway."""
        self._move_along_path()
        
        # Sprawdź czy dotarł do stanowiska
        if self.current_node == self.target_node:
            self.model.segment_manager.release_edges(self.blocked_edges, self.unique_id)
            self.blocked_edges = []
            self.state = "waiting_departure"
            self.target_node = None
            self.path = []
    
    
    def wait_for_departure(self):
        """Oczekiwanie na pozwolenie na start"""
        if not self.is_in_queue:
            self.model.runway_controller.add_to_runway_queue(self)
            self.is_in_queue = True

    
    def depart(self):
        """Proces startu i odlotu - samolot startuje z pasa"""
        self.departure_time += 1
        self._move_along_path()
        if self.current_node == self.target_node:
            # Samolot odleciał - usuń z symulacji
            self.model.segment_manager.release_edges(self.blocked_edges, self.unique_id)
            self.blocked_edges = []
            self.model.runway_controller.finish_departure()
            if self.current_node is not None:
                self.model.segment_manager.release_node(self.current_node, self.unique_id)
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
            if self.state == "taxiing_to_runway":
                self._prepare_taxi_to_runway_path()
            elif self.target_node and self.current_node:
                self.path = self.model.graph.find_shortest_path(self.current_node, self.target_node)
                if len(self.path) > 1:
                    self.path.pop(0)
        
        if self.path:
            next_node = self.path[0]

            # Oblicz czas ruchu dla tej krawędzi (potrzebujemy duration dla interpolacji)
            start_pos = self.model.graph.get_node_position(self.current_node)
            target_pos = self.model.graph.get_node_position(next_node)
            edge_type = self.model.graph.get_edge_type(self.current_node, next_node)
            if start_pos and target_pos:
                distance = self.movement_controller.calculate_distance(start_pos, target_pos)
                if edge_type == "runway":
                    movement_type = "landing" if self.state == "landing" else "departing"
                else:
                    movement_type = self.movement_controller.get_movement_type_for_state(self.state)
                estimated_duration = self.movement_controller.calculate_movement_time(distance, movement_type)
            else:
                estimated_duration = 10  # fallback

            # Segment zarezerwowany - rozpocznij ruch
            self._start_movement_to_node(next_node)
            self.path.pop(0)
            self.wait_time = 0
            self.waiting_for_segment = None
            # Wyczyść stan oczekiwania
            self.blocked_by_airplane = None
            self.waiting_position = None
            self.queue_position = 0

            if self.state == "taxiing_to_runway" and edge_type == "runway":
                atc = getattr(self.model.segment_manager, "atc", None)
                if atc:
                    atc.grant_line_up(self.model.step_count)
 
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
        
        target = self.position.target_node
        if target is not None:
            node_busy = not self.model.segment_manager.request_node(target, self.unique_id)
            
            if node_busy:
                if self.hold_progress_limit is None:
                    self.hold_progress_limit = 0.85

                if self.position.progress >= self.hold_progress_limit:
                    return
            else:
                if self.hold_progress_limit is not None:
                    self.hold_progress_limit = None

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
                self.model.segment_manager.release_edge(prev_node, finished_target, self.unique_id)
                # Zwolnij poprzedni węzeł (teraz jesteśmy już w docelowym)
                self.model.segment_manager.release_node(prev_node, self.unique_id)
        
        self.is_moving = False
        self.position.progress = 0.0
        self.position.current_node = self.current_node
        self.position.target_node = None
    
    def is_node_free(self, node_id):
        """Sprawdza czy węzeł jest wolny"""
        for agent in self.model.airplanes:
            if agent != self and hasattr(agent, 'current_node') and agent.current_node == node_id:
                return False
        return True
    
    def get_position(self):
        """Zwraca pozycję samolotu z interpolacją + wizualna kolejka przy entry/exit."""
        x, y = self.position.x, self.position.y

        if self.current_node is not None:
            same_node_planes = [
                a for a in self.model.airplanes
                if a is not self and a.current_node == self.current_node
            ]

            if same_node_planes:
                all_planes = sorted(same_node_planes + [self], key=lambda a: a.unique_id)
                idx = all_planes.index(self)

                direction = 0
                try:
                    G = self.model.graph.graph
                    neighbors = G[self.current_node]
                    has_exit = any(data.get("type") == "runway_exit" for _, data in neighbors.items())
                    has_entry = any(data.get("type") == "runway_entry" for _, data in neighbors.items())
                    if has_exit:
                        direction = 1
                    elif has_entry:
                        direction = -1
                except Exception:
                    direction = 0

                offset = 0.8
                y += direction * idx * offset

        return (x, y)

    
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
