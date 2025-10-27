import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional

class AirportGraph:
    """
    Klasa reprezentująca strukturę lotniska jako graf
    """
    
    def __init__(self, nodes_file: str, edges_file: str):
        """
        Inicjalizacja grafu lotniska z plików CSV
        
        Args:
            nodes_file: ścieżka do pliku nodes.csv
            edges_file: ścieżka do pliku edges.csv
        """
        self.nodes_df = pd.read_csv(nodes_file)
        self.edges_df = pd.read_csv(edges_file)
        
        # Tworzenie grafu NetworkX
        self.graph = nx.Graph()
        
        # Dodawanie węzłów
        for _, node in self.nodes_df.iterrows():
            self.graph.add_node(
                node['id'],
                type=node['type'],
                name=node['name'],
                x=node['x'],
                y=node['y'],
                notes=node['notes']
            )
        
        # Dodawanie krawędzi
        for _, edge in self.edges_df.iterrows():
            self.graph.add_edge(
                edge['from'],
                edge['to'],
                type=edge['type'],
                length=edge['length'],
                bidirectional=edge['bidirectional']
            )
    
    def get_node_by_id(self, node_id: int) -> Optional[Dict]:
        """Pobiera węzeł po ID"""
        if node_id in self.graph.nodes:
            return self.graph.nodes[node_id]
        return None
    
    def get_node_position(self, node_id: int) -> Optional[Tuple[int, int]]:
        """Pobiera pozycję węzła (x, y)"""
        node = self.get_node_by_id(node_id)
        if node:
            return (node['x'], node['y'])
        return None
    
    def get_neighbors(self, node_id: int) -> List[int]:
        """Pobiera sąsiadów węzła"""
        return list(self.graph.neighbors(node_id))
    
    def get_nodes_by_type(self, node_type: str) -> List[int]:
        """Pobiera wszystkie węzły określonego typu"""
        return [node_id for node_id, data in self.graph.nodes(data=True) 
                if data['type'] == node_type]
    
    def get_runway_nodes(self) -> List[int]:
        """Pobiera węzły pasów startowych"""
        return self.get_nodes_by_type('runway_thr')
    
    def get_stand_nodes(self) -> List[int]:
        """Pobiera węzły stanowisk postojowych"""
        return self.get_nodes_by_type('stand')
    
    def get_apron_nodes(self) -> List[int]:
        """Pobiera węzły płyt postojowych"""
        return self.get_nodes_by_type('apron')
    
    def get_taxiway_nodes(self) -> List[int]:
        """Pobiera węzły dróg kołowania"""
        return self.get_nodes_by_type('taxiway')
    
    def find_shortest_path(self, start: int, end: int) -> List[int]:
        """Znajduje najkrótszą ścieżkę między dwoma węzłami"""
        try:
            return nx.shortest_path(self.graph, start, end)
        except nx.NetworkXNoPath:
            return []
    
    def get_edge_length(self, from_node: int, to_node: int) -> float:
        """Pobiera długość krawędzi między węzłami"""
        if self.graph.has_edge(from_node, to_node):
            return self.graph[from_node][to_node]['length']
        return 0.0
    
    def get_all_nodes(self) -> List[int]:
        """Pobiera wszystkie węzły"""
        return list(self.graph.nodes())
    
    def get_graph_bounds(self) -> Tuple[int, int, int, int]:
        """Pobiera granice grafu (min_x, max_x, min_y, max_y)"""
        x_coords = [data['x'] for _, data in self.graph.nodes(data=True)]
        y_coords = [data['y'] for _, data in self.graph.nodes(data=True)]
        
        return (min(x_coords), max(x_coords), min(y_coords), max(y_coords))
    
    def is_connected(self, node1: int, node2: int) -> bool:
        """Sprawdza czy węzły są połączone"""
        return self.graph.has_edge(node1, node2)
    
    def get_edge_type(self, from_node: int, to_node: int) -> Optional[str]:
        """Pobiera typ krawędzi między węzłami"""
        if self.graph.has_edge(from_node, to_node):
            return self.graph[from_node][to_node]['type']
        return None
