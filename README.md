# Symulacja Lotniska z Pasem Startowym - Mesa (Wersja z Grafem)

Projekt symuluje ruch samolotów na lotnisku z pasem startowym przy użyciu frameworka Mesa. Symulacja wykorzystuje strukturę grafu do reprezentacji lotniska, gdzie węzły reprezentują różne obszary lotniska (pasy startowe, stanowiska postojowe, drogi kołowania), a krawędzie reprezentują połączenia między nimi.

## Struktura Projektu

- **src/**: Zawiera główny kod źródłowy symulacji.

  - **graph.py**: Klasa `AirportGraph` do reprezentacji struktury lotniska jako graf
  - **agents/**: Katalog zawierający agenty symulacji
    - **airplane.py**: Definiuje klasę `Airplane` z właściwościami i metodami dla zachowania samolotów
    - **runway_controler.py**: Definiuje klasę `RunwayController` do kontroli pasa startowego
  - **model.py**: Zawiera klasę `AirportModel` zarządzającą środowiskiem symulacji
  - **visualization.py**: Obsługuje wizualizację symulacji z animacjami i statystykami
  - **balice_layout.py**: Stary układ siatki (zachowany dla kompatybilności)

- **nodes.csv**: Plik definiujący węzły grafu lotniska (ID, typ, nazwa, pozycja X/Y, notatki)
- **edges.csv**: Plik definiujący krawędzie grafu (od, do, typ, długość, dwukierunkowość)

- **notebooks/**: Zawiera notebooki Jupyter do eksploracyjnej analizy danych.

  - **exploration.ipynb**: Używany do analizy i wizualizacji wyników symulacji.

- **data/**: Przechowuje pliki danych związane z symulacją.

  - **runway_logs.csv**: Logi ruchów samolotów na pasie startowym.

- **tests/**: Zawiera testy jednostkowe dla projektu.

  - **test_model.py**: Testy jednostkowe dla klasy `AirportModel`.

- **requirements.txt**: Lista zależności wymaganych dla projektu.

- **run_simulation.py**: Główny plik uruchamiający symulację.
- **realtime_animation.py**: Skrypt do uruchomienia animacji w czasie rzeczywistym.

## Struktura Grafu Lotniska

Symulacja wykorzystuje graf skierowany do reprezentacji lotniska:

### Typy Węzłów:

- **runway_thr**: Progi pasów startowych (RWY_07, RWY_25)
- **taxiway**: Drogi kołowania (TWY_B_NORTH, TWY_B_SOUTH)
- **apron**: Płyty postojowe (APRON_MAIN, MIL_APRON_1, MIL_APRON_2)
- **stand**: Stanowiska postojowe (STAND_1 do STAND_6)
- **connector**: Łączniki między różnymi obszarami

### Typy Krawędzi:

- **taxi**: Drogi kołowania między węzłami
- **apron_link**: Połączenia z płytami postojowymi
- **stand_link**: Połączenia ze stanowiskami postojowymi
- **connector**: Łączniki między różnymi obszarami

## Instrukcje Instalacji

1. Sklonuj repozytorium na swoją maszynę lokalną.
2. Przejdź do katalogu projektu.
3. Zainstaluj wymagane zależności używając:
   ```
   pip install -r requirements.txt
   ```

## Uruchamianie Symulacji

### Opcja 1: Główny skrypt

```bash
python run_simulation.py
```

Skrypt oferuje kilka opcji:

1. **Animacja interaktywna** - pokazuje animację w czasie rzeczywistym
2. **Statyczny obraz** - pokazuje jeden obraz stanu symulacji
3. **Zapisz animację** - zapisuje animację do pliku GIF
4. **Pełna symulacja** - uruchamia pełną symulację i pokazuje statystyki

### Opcja 2: Szybka demonstracja

```bash
python run_simulation.py --demo
```

### Opcja 3: Animacja w czasie rzeczywistym

```bash
python realtime_animation.py
```

### Opcja 4: Notebook Jupyter

```bash
jupyter notebook exploration.ipynb
```

## Przegląd Symulacji

Symulacja modeluje zachowanie samolotów podczas ich ruchu po grafie lotniska, zbliżania się do pasa startowego i lądowania na podstawie zdefiniowanych reguł.

### Agenty:

- **Samoloty (Airplane)**: Poruszają się po grafie lotniska w różnych stanach:

  - `waiting` (niebieski trójkąt) - oczekują na pozwolenie na lądowanie
  - `landing` (czerwone koło) - lądują na pasie startowym
  - `landed` (zielony diament) - wylądowały
  - `taxiing` (pomarańczowy kwadrat) - taxi do stanowiska postojowego

- **Kontroler Pasa Startowego (RunwayController)**: Zarządza dostępem do pasa startowego, tworzy kolejkę samolotów oczekujących na lądowanie.

### Funkcje Wizualizacji:

- **Graf lotniska** z różnymi kolorami dla różnych typów węzłów
- **Animacja w czasie rzeczywistym** z różnymi kształtami dla różnych stanów samolotów
- **Statystyki symulacji** pokazujące liczbę samolotów w każdym stanie w czasie
- **Informacje o stanie** wyświetlane na wykresie
- **Legenda** wyjaśniająca kolory i kształty

## Parametry Symulacji

Możesz dostosować parametry symulacji w pliku `run_simulation.py`:

- `num_airplanes` - liczba samolotów (domyślnie 8)
- `nodes_file` - plik z węzłami grafu (domyślnie "nodes.csv")
- `edges_file` - plik z krawędziami grafu (domyślnie "edges.csv")

## Wymagania Systemowe

- Python 3.7+
- Mesa 3.3.0
- matplotlib 3.9.2
- networkx 3.3
- numpy 2.3.4
- pandas 2.3.3

## Wkład w Projekt

Wkład w projekt jest mile widziany. Proszę przesłać pull request lub otworzyć issue dla wszelkich sugestii lub ulepszeń.
