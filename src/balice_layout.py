# src/maps/balice_layout.py

"""
Uproszczony układ cywilnego lotniska Kraków-Balice (EPKK)
Autor: Robert Jacak + ChatGPT
"""

BALICE_MAP = [
    # Każdy wiersz to rząd siatki (y), kolumny to x
    # R = runway, T = taxiway, A = apron, M = terminal, G = grass
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
    list("GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"),
]

# Teraz wypełniamy kluczowe strefy
# Runway (07/25)
for x in range(3, 27):
    BALICE_MAP[5][x] = "R"

# Taxiways B1–B6 (łączą terminal z pasem)
BALICE_MAP[4][5] = "T"   # B1
BALICE_MAP[4][9] = "T"   # B2
BALICE_MAP[4][13] = "T"  # B3
BALICE_MAP[4][17] = "T"  # B4
BALICE_MAP[4][21] = "T"  # B5
BALICE_MAP[4][25] = "T"  # B6

# Apron (płyta postojowa)
for x in range(4, 26):
    BALICE_MAP[3][x] = "A"

# Terminal
for x in range(6, 24):
    BALICE_MAP[2][x] = "M"