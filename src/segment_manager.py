import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ConflictResolution(Enum):
    """Typy rozwiązań konfliktów"""
    FIRST_COME_FIRST_SERVED = "first_come_first_served"
    PRIORITY_BASED = "priority_based"
    NEGOTIATION = "negotiation"
    CONTROLLER_DECISION = "controller_decision"

@dataclass
class SegmentReservation:
    """Rezerwacja segmentu lotniska"""
    segment_id: int
    airplane_id: int
    start_time: int
    end_time: int
    priority: int = 1  # Wyższa liczba = wyższy priorytet
    reservation_type: str = "movement"  # movement, holding, emergency

@dataclass
class ConflictProposal:
    """Propozycja rozwiązania konfliktu"""
    from_airplane: int
    to_airplane: int
    proposal_type: str  # "wait", "alternative_route", "priority_swap"
    details: Dict
    timestamp: int

class SegmentManager:
    """Zarządza rezerwacjami segmentów lotniska i rozwiązywaniem konfliktów"""
    
    def __init__(self, model=None):
        self.reservations: Dict[int, List[SegmentReservation]] = {}  # segment_id -> reservations
        self.conflict_proposals: List[ConflictProposal] = []
        self.airplane_priorities: Dict[int, int] = {}  # airplane_id -> priority
        self.reservation_counter = 0
        self.model = model  # Referencja do modelu
        
        # Rezerwacje krawędzi (bez wymijania) - klucz jako krawędź nieskierowana
        # edge_key = (min(u,v), max(u,v)) -> List[SegmentReservation]
        self.edge_reservations: Dict[Tuple[int, int], List[SegmentReservation]] = {}
        
        # Rezerwacje węzłów (tylko 1 samolot w węźle) - node_id -> List[SegmentReservation]
        self.node_reservations: Dict[int, List[SegmentReservation]] = {}

        # Zestaw węzłów należących do pasa startowego (na podstawie krawędzi typu 'runway')
        self.runway_nodes: set[int] = set()
        if self.model is not None and hasattr(self.model, "graph"):
            try:
                for u, v, data in self.model.graph.graph.edges(data=True):
                    if data.get("type") == "runway":
                        self.runway_nodes.add(int(u))
                        self.runway_nodes.add(int(v))
            except Exception:
                # W razie problemów z odczytem grafu pozostaw pusty zestaw
                self.runway_nodes = set()
        
    def set_airplane_priority(self, airplane_id: int, priority: int):
        """Ustawia priorytet samolotu"""
        self.airplane_priorities[airplane_id] = priority
    
    def request_segment(self, segment_id: int, airplane_id: int, 
                       duration: int, current_time: int) -> Tuple[bool, Optional[str]]:
        """
        Próbuje zarezerwować segment lotniska
        
        Returns:
            (success, conflict_airplane_id) - czy udało się zarezerwować i ID samolotu w konflikcie
        """
        # Specjalna logika dla pasa startowego - tylko 1 samolot naraz
        if self._is_runway_segment(segment_id):
            return self._request_runway_segment(segment_id, airplane_id, duration, current_time)
        
        if segment_id not in self.reservations:
            self.reservations[segment_id] = []
        
        # Sprawdź czy segment jest wolny w danym czasie
        requested_start = current_time
        requested_end = current_time + duration
        
        for reservation in self.reservations[segment_id]:
            # Sprawdź czy rezerwacje się nakładają
            if not (requested_end <= reservation.start_time or requested_start >= reservation.end_time):
                # Konflikt! Sprawdź priorytety
                airplane_priority = self.airplane_priorities.get(airplane_id, 1)
                reservation_priority = self.airplane_priorities.get(reservation.airplane_id, 1)
                
                if airplane_priority > reservation_priority:
                    # Wyższy priorytet - usuń starą rezerwację
                    self.reservations[segment_id].remove(reservation)
                    break
                elif airplane_priority < reservation_priority:
                    # Niższy priorytet - nie można zarezerwować
                    return False, reservation.airplane_id
                else:
                    # Równy priorytet - potrzebna negocjacja
                    return False, reservation.airplane_id
        
        # Segment wolny - dodaj rezerwację
        reservation = SegmentReservation(
            segment_id=segment_id,
            airplane_id=airplane_id,
            start_time=requested_start,
            end_time=requested_end,
            priority=self.airplane_priorities.get(airplane_id, 1)
        )
        self.reservations[segment_id].append(reservation)
        self.reservation_counter += 1
        
        return True, None
    
    def _is_runway_segment(self, segment_id: int) -> bool:
        """Sprawdza czy dany węzeł leży na pasie startowym (jako koniec krawędzi typu 'runway')."""
        if not self.runway_nodes and self.model is not None and hasattr(self.model, "graph"):
            # Spróbuj zbudować ponownie (np. gdy graf był później gotowy)
            try:
                for u, v, data in self.model.graph.graph.edges(data=True):
                    if data.get("type") == "runway":
                        self.runway_nodes.add(int(u))
                        self.runway_nodes.add(int(v))
            except Exception:
                return False
        return segment_id in self.runway_nodes
    
    def _request_runway_segment(self, segment_id: int, airplane_id: int, 
                              duration: int, current_time: int) -> Tuple[bool, Optional[str]]:
        """Specjalna logika rezerwacji pasa startowego - tylko 1 samolot naraz"""
        # Sprawdź czy jakikolwiek samolot już używa pasa startowego (dowolny węzeł z pasa)
        for seg_id in list(self.runway_nodes):
            if seg_id in self.reservations:
                for reservation in self.reservations[seg_id]:
                    # Sprawdź czy rezerwacja jest aktywna
                    if reservation.start_time <= current_time <= reservation.end_time:
                        return False, reservation.airplane_id
        
        # Sprawdź też czy jakikolwiek samolot jest na pasie (stoi lub porusza się po krawędzi runway)
        if self.model is not None:
            for airplane in self.model.airplanes:
                if airplane.unique_id == airplane_id:
                    continue
                # Stoi na węźle należącym do pasa
                if getattr(airplane, "current_node", None) in self.runway_nodes:
                    return False, airplane.unique_id
                # Porusza się po krawędzi i krawędź to runway
                if getattr(airplane, "is_moving", False):
                    u = getattr(airplane.position, "current_node", None)
                    v = getattr(airplane.position, "target_node", None)
                    if u is not None and v is not None and self.model.graph.get_edge_type(u, v) == "runway":
                        return False, airplane.unique_id
        
        # Pas wolny - dodaj rezerwację
        if segment_id not in self.reservations:
            self.reservations[segment_id] = []
        
        reservation = SegmentReservation(
            segment_id=segment_id,
            airplane_id=airplane_id,
            start_time=current_time,
            end_time=current_time + duration,
            priority=self.airplane_priorities.get(airplane_id, 1)
        )
        self.reservations[segment_id].append(reservation)
        self.reservation_counter += 1
        
        return True, None
    
    def request_segment_with_no_passing(self, segment_id: int, airplane_id: int, 
                                       duration: int, current_time: int) -> Tuple[bool, Optional[str]]:
        """
        Próbuje zarezerwować segment z zakazem wymijania się
        Samoloty muszą czekać w kolejce na drogach
        """
        # Specjalna logika dla pasa startowego
        if self._is_runway_segment(segment_id):
            return self._request_runway_segment(segment_id, airplane_id, duration, current_time)
        
        if segment_id not in self.reservations:
            self.reservations[segment_id] = []
        
        # Sprawdź czy segment jest wolny
        requested_start = current_time
        requested_end = current_time + duration
        
        # Znajdź wszystkie aktywne rezerwacje dla tego segmentu
        active_reservations = []
        for reservation in self.reservations[segment_id]:
            if not (requested_end <= reservation.start_time or requested_start >= reservation.end_time):
                active_reservations.append(reservation)
        
        if active_reservations:
            # Segment zajęty - nie można wymijać
            return False, active_reservations[0].airplane_id
        
        # Segment wolny - dodaj rezerwację
        reservation = SegmentReservation(
            segment_id=segment_id,
            airplane_id=airplane_id,
            start_time=requested_start,
            end_time=requested_end,
            priority=self.airplane_priorities.get(airplane_id, 1)
        )
        self.reservations[segment_id].append(reservation)
        self.reservation_counter += 1
        
        return True, None
    
    def release_segment(self, segment_id: int, airplane_id: int, current_time: int):
        """Zwolnij segment lotniska"""
        if segment_id in self.reservations:
            self.reservations[segment_id] = [
                r for r in self.reservations[segment_id] 
                if not (r.airplane_id == airplane_id and r.start_time <= current_time <= r.end_time)
            ]

    def _edge_key(self, u: int, v: int) -> Tuple[int, int]:
        return (u, v) if u <= v else (v, u)

    def request_node(self, node_id: int, airplane_id: int, duration: int, current_time: int) -> Tuple[bool, Optional[int]]:
        """Rezerwuje węzeł (tylko 1 samolot w węźle).
        Zwraca (True, None) albo (False, blocking_airplane_id)."""
        if node_id not in self.node_reservations:
            self.node_reservations[node_id] = []
        
        req_start = current_time
        req_end = current_time + duration
        
        # Sprawdź czy węzeł jest wolny
        for res in self.node_reservations[node_id]:
            if not (req_end <= res.start_time or req_start >= res.end_time):
                return False, res.airplane_id
        
        # Dodaj rezerwację węzła
        reservation = SegmentReservation(segment_id=node_id, airplane_id=airplane_id,
                                         start_time=req_start, end_time=req_end,
                                         priority=self.airplane_priorities.get(airplane_id, 1))
        self.node_reservations[node_id].append(reservation)
        return True, None
    
    def release_node(self, node_id: int, airplane_id: int, current_time: int):
        """Zwalnia rezerwację węzła."""
        if node_id in self.node_reservations:
            self.node_reservations[node_id] = [
                r for r in self.node_reservations[node_id]
                if not (r.airplane_id == airplane_id and r.start_time <= current_time <= r.end_time)
            ]

    def request_edge_with_no_passing(self, u: int, v: int, airplane_id: int,
                                     duration: int, current_time: int) -> Tuple[bool, Optional[int]]:
        """Rezerwuje krawędź (u,v) i węzeł docelowy v bez możliwości wymijania.
        Zwraca (True, None) albo (False, blocking_airplane_id)."""
        key = self._edge_key(u, v)

        # Najpierw sprawdź węzeł docelowy - czy jest wolny
        node_ok, node_blocker = self.request_node(v, airplane_id, duration, current_time)
        if not node_ok:
            return False, node_blocker

        # Specjalna logika pasa: jeśli to krawędź runway, blokuj cały pas
        edge_type = None
        if self.model is not None:
            edge_type = self.model.graph.get_edge_type(u, v)
        if edge_type == "runway":
            # wykorzystaj logikę _request_runway_segment
            ok, blocker = self._request_runway_segment(v, airplane_id, duration, current_time)
            if not ok:
                # Cofnij rezerwację węzła
                self.release_node(v, airplane_id, current_time)
                return False, blocker

        if key not in self.edge_reservations:
            self.edge_reservations[key] = []

        req_start = current_time
        req_end = current_time + duration

        # Nie pozwalaj na nakładanie na tej krawędzi
        for res in self.edge_reservations[key]:
            if not (req_end <= res.start_time or req_start >= res.end_time):
                # Cofnij rezerwację węzła
                self.release_node(v, airplane_id, current_time)
                return False, res.airplane_id

        # Dodaj rezerwację krawędzi
        reservation = SegmentReservation(segment_id=-1, airplane_id=airplane_id,
                                         start_time=req_start, end_time=req_end,
                                         priority=self.airplane_priorities.get(airplane_id, 1))
        self.edge_reservations[key].append(reservation)
        return True, None

    def release_edge(self, u: int, v: int, airplane_id: int, current_time: int):
        """Zwalnia rezerwację krawędzi (u,v) dla danego samolotu."""
        key = self._edge_key(u, v)
        if key in self.edge_reservations:
            self.edge_reservations[key] = [
                r for r in self.edge_reservations[key]
                if not (r.airplane_id == airplane_id and r.start_time <= current_time <= r.end_time)
            ]
    
    def create_conflict_proposal(self, from_airplane: int, to_airplane: int, 
                               proposal_type: str, details: Dict, current_time: int):
        """Tworzy propozycję rozwiązania konfliktu"""
        proposal = ConflictProposal(
            from_airplane=from_airplane,
            to_airplane=to_airplane,
            proposal_type=proposal_type,
            details=details,
            timestamp=current_time
        )
        self.conflict_proposals.append(proposal)
        return proposal
    
    def get_conflict_proposals_for_airplane(self, airplane_id: int) -> List[ConflictProposal]:
        """Pobiera propozycje konfliktów dla danego samolotu"""
        return [p for p in self.conflict_proposals if p.to_airplane == airplane_id]
    
    def resolve_conflict_by_controller(self, segment_id: int, airplane1: int, 
                                     airplane2: int, current_time: int) -> int:
        """
        Kontroler rozstrzyga konflikt
        Returns: ID samolotu który wygrywa
        """
        priority1 = self.airplane_priorities.get(airplane1, 1)
        priority2 = self.airplane_priorities.get(airplane2, 1)
        
        if priority1 > priority2:
            winner = airplane1
        elif priority2 > priority1:
            winner = airplane2
        else:
            # Równy priorytet - pierwszy który zgłosił
            winner = airplane1  # Można dodać bardziej zaawansowaną logikę
        
        # Usuń przegraną rezerwację
        if segment_id in self.reservations:
            self.reservations[segment_id] = [
                r for r in self.reservations[segment_id] 
                if not (r.airplane_id != winner and r.start_time <= current_time <= r.end_time)
            ]
        
        return winner
    
    def cleanup_old_reservations(self, current_time: int):
        """Usuwa stare rezerwacje"""
        for segment_id in self.reservations:
            self.reservations[segment_id] = [
                r for r in self.reservations[segment_id] 
                if r.end_time > current_time
            ]
    
    def get_segment_status(self, segment_id: int, current_time: int) -> Dict:
        """Zwraca status segmentu"""
        if segment_id not in self.reservations:
            return {"status": "free", "reserved_by": None}
        
        for reservation in self.reservations[segment_id]:
            if reservation.start_time <= current_time <= reservation.end_time:
                return {
                    "status": "occupied", 
                    "reserved_by": reservation.airplane_id,
                    "until": reservation.end_time
                }
        
        return {"status": "free", "reserved_by": None}
