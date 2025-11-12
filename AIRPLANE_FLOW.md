# Flow Samolotu - Dokumentacja

## Przegląd Stanów

Samolot przechodzi przez następujące stany:

### Dla samolotów przybywających (arrival):

1. `waiting_landing` → `landing` → `taxiing_to_exit` → `at_exit` → `taxiing_to_stand` → `at_stand`

### Dla samolotów odlatujących (departure):

2. `at_stand` → `pushback_pending` → `pushback` → `waiting_departure` → `departing`

---

## Szczegółowy Flow

### 1. **waiting_landing** (Oczekiwanie na lądowanie)

**Lokalizacja:** W powietrzu (poza grafem, `current_node = None`)

**Co się dzieje:**

- Samolot dodaje się do kolejki pasa startowego (`runway_controller.runway_queue`)
- Ustawia `is_in_queue = True`
- **OCZEKUJE** na zgodę ATC i dostępność pasa

**Przejście do następnego stanu:**

- Gdy `RunwayController` wybierze samolot z kolejki i:
  - Dla arrival: wywoła `choose_exit()` → zarezerwuje `taxiway_outbound` → zarezerwuje `runway`
  - Ustawi `state = "landing"` w `_start_operation()`

**Metoda:** `wait_for_landing()` (linia 73-77)

---

### 2. **landing** (Lądowanie)

**Lokalizacja:** Na pasie startowym (`current_node = active_runway`)

**Co się dzieje:**

- Samolot **PORUSZA SIĘ** po pasie (`_move_along_path()`)
- Zwiększa `landing_time` o 1 w każdym kroku
- Używa prędkości `movement_type = "landing"` (4.0 jednostek/tick)
- Po `max_landing_time = 3` krokach kończy lądowanie

**Przejście do następnego stanu:**

- Gdy `landing_time >= max_landing_time`:
  - `state = "taxiing_to_exit"`
  - `landing_time = 0`
  - `runway_controller.finish_landing()` (zwalnia pas)

**Metoda:** `land()` (linia 79-89)

**UWAGA:** Samolot już ma zarezerwowane `taxiway_outbound` i `runway` z poprzedniego stanu.

---

### 3. **taxiing_to_exit** (Taxi do wyjścia z pasa)

**Lokalizacja:** Na pasie startowym, porusza się do wyjścia

**Co się dzieje:**

- Samolot **PORUSZA SIĘ** po ścieżce do `target_node` (wyjście z pasa)
- Używa `_move_along_path()` do poruszania się
- Ma zarezerwowane `blocked_edges` (taxiway_outbound + runway)

**Przejście do następnego stanu:**

- Gdy `current_node == target_node`:
  - Zwolnienie `blocked_edges`
  - `state = "at_exit"`
  - `target_node = None`
  - `path = []`

**Metoda:** `taxi_to_exit()` (linia 105-113)

---

### 4. **at_exit** (Na wyjściu z pasa)

**Lokalizacja:** Na węźle wyjścia z pasa (`current_node = wyjście z pasa`)

**Co się dzieje:**

- Samolot **OCZEKUJE** na dostępność:
  - `taxiway` (wszystkie krawędzie typu taxiway)
  - `apron` (wszystkie krawędzie typu stand_link)
  - Wolnego stanowiska (`choose_stand()`)

**Przejście do następnego stanu:**

- Gdy wszystkie rezerwacje się powiodą:
  - `state = "taxiing_to_stand"`
  - `blocked_edges` zawiera taxiway + apron

**Metoda:** `wait_for_stand()` (linia 115-127)

**UWAGA:** Jeśli rezerwacje się nie powiodą, samolot pozostaje w tym stanie i próbuje ponownie w następnym kroku.

---

### 5. **taxiing_to_stand** (Taxi do stanowiska)

**Lokalizacja:** Na taxiway/apron, porusza się do stanowiska

**Co się dzieje:**

- Samolot **PORUSZA SIĘ** po ścieżce do `target_node` (stanowisko)
- Używa `_move_along_path()` z prędkością `movement_type = "taxiing"` (0.5 jednostek/tick)
- Ma zarezerwowane `blocked_edges` (taxiway + apron)

**Przejście do następnego stanu:**

- Gdy `current_node == target_node`:
  - Zwolnienie `blocked_edges`
  - `state = "at_stand"`
  - `stand_time = 0`

**Metoda:** `taxi_to_stand()` (linia 152-161)

---

### 6. **at_stand** (Na stanowisku postojowym)

**Lokalizacja:** Na węźle stanowiska (`current_node = stanowisko`)

**Co się dzieje:**

- Samolot **OCZEKUJE** na obsługę
- Zwiększa `stand_time` o 1 w każdym kroku
- Po `max_stand_time = 10` krokach kończy obsługę

**Przejście do następnego stanu:**

- Gdy `stand_time >= max_stand_time`:
  - `state = "pushback_pending"`
  - `runway_entry_node = runway_controller.get_runway_entry_node()`
  - `target_node = None`
  - `path = []`

**Metoda:** `at_stand_service()` (linia 163-173)

---

### 7. **pushback_pending** (Oczekiwanie na pushback)

**Lokalizacja:** Na stanowisku (`current_node = stanowisko`)

**Co się dzieje:**

- Samolot **OCZEKUJE** na dostępność:
  - `apron` (wszystkie krawędzie typu stand_link)
  - `taxiway` (wszystkie krawędzie typu taxiway)
  - `runway_entry` (wybór wejścia na pas przez `choose_runway_entry()`)

**Przejście do następnego stanu:**

- Gdy wszystkie rezerwacje się powiodą:
  - `state = "pushback"`
  - `airplane_type = "departure"`
  - `pushback_started_at = now`
  - `blocked_edges` zawiera apron + taxiway + runway_entry

**Metoda:** `handle_pushback_pending()` (linia 175-191)

**UWAGA:** Jeśli rezerwacje się nie powiodą, samolot pozostaje w tym stanie i próbuje ponownie w następnym kroku.

---

### 8. **pushback** (Pushback - wypychanie)

**Lokalizacja:** Na apron/taxiway, porusza się do punktu wejścia na pas

**Co się dzieje:**

- Samolot **PORUSZA SIĘ** po ścieżce do `target_node` (punkt wejścia na pas)
- Używa `_move_along_path()` z prędkością `movement_type = "taxiing"` (0.5 jednostek/tick)
- Ma zarezerwowane `blocked_edges` (apron + taxiway + runway_entry)

**Przejście do następnego stanu:**

- Gdy `current_node == target_node`:
  - Zwolnienie `blocked_edges`
  - `state = "waiting_departure"`
  - `target_node = None`
  - `path = []`

**Metoda:** `handle_pushback()` (linia 213-223)

---

### 9. **waiting_departure** (Oczekiwanie na start)

**Lokalizacja:** Na punkcie wejścia na pas (`current_node = runway_entry`)

**Co się dzieje:**

- Samolot dodaje się do kolejki pasa startowego (`runway_controller.runway_queue`)
- Ustawia `is_in_queue = True`
- **OCZEKUJE** na zgodę ATC i dostępność pasa

**Przejście do następnego stanu:**

- Gdy `RunwayController` wybierze samolot z kolejki i:
  - Zarezerwuje `runway`
  - Ustawi `state = "departing"` w `_start_operation()`
  - Ustawi `target_node = active_runway`
  - Wyznaczy ścieżkę do pasa

**Metoda:** `wait_for_departure()` (linia 226-230)

---

### 10. **departing** (Start)

**Lokalizacja:** Na pasie startowym, porusza się wzdłuż pasa

**Co się dzieje:**

- Samolot **PORUSZA SIĘ** po pasie (`_move_along_path()`)
- Zwiększa `departure_time` o 1 w każdym kroku
- Używa prędkości `movement_type = "departing"` (4.0 jednostek/tick)
- Ma zarezerwowane `blocked_edges` (runway)

**Przejście do następnego stanu:**

- Gdy `current_node == target_node` (koniec pasa):
  - Zwolnienie `blocked_edges`
  - `runway_controller.finish_departure()` (zwalnia pas)
  - Zwolnienie węzła
  - **Usunięcie z symulacji** (`self.model.airplanes.remove(self)`)

**Metoda:** `depart()` (linia 233-245)

---

## Miejsca Oczekiwania

### 1. **waiting_landing**

- **Gdzie:** W powietrzu (poza grafem)
- **Dlaczego:** Oczekuje na zgodę ATC i dostępność pasa
- **Kolejka:** `runway_controller.runway_queue`
- **Warunek przejścia:** Zgoda ATC + rezerwacja `taxiway_outbound` + rezerwacja `runway`

### 2. **at_exit**

- **Gdzie:** Na węźle wyjścia z pasa
- **Dlaczego:** Oczekuje na dostępność taxiway + apron + wolnego stanowiska
- **Warunek przejścia:** Rezerwacja `taxiway` + `apron` + `choose_stand()` = True

### 3. **pushback_pending**

- **Gdzie:** Na stanowisku
- **Dlaczego:** Oczekuje na dostępność apron + taxiway + runway_entry
- **Warunek przejścia:** Rezerwacja `apron` + `taxiway` + `runway_entry` (przez `choose_runway_entry()`)

### 4. **waiting_departure**

- **Gdzie:** Na punkcie wejścia na pas (runway_entry)
- **Dlaczego:** Oczekuje na zgodę ATC i dostępność pasa
- **Kolejka:** `runway_controller.runway_queue`
- **Warunek przejścia:** Zgoda ATC + rezerwacja `runway`

---

## Rezerwacje Segmentów

### Kiedy są rezerwowane:

1. **Przed lądowaniem:** `taxiway_outbound` + `runway` (w `RunwayController.step()`)
2. **Przed taxi do stanowiska:** `taxiway` + `apron` (w `wait_for_stand()`)
3. **Przed pushbackiem:** `apron` + `taxiway` + `runway_entry` (w `handle_pushback_pending()`)
4. **Przed startem:** `runway` (w `RunwayController.step()`)

### Kiedy są zwalniane:

1. **Po zjechaniu z pasa:** W `taxi_to_exit()` gdy `current_node == target_node`
2. **Po dotarciu do stanowiska:** W `taxi_to_stand()` gdy `current_node == target_node`
3. **Po pushbacku:** W `handle_pushback()` gdy `current_node == target_node`
4. **Po starcie:** W `depart()` gdy `current_node == target_node`

---

## Prędkości Ruchu

- **taxiing:** 0.5 jednostek/tick (wolny ruch po taxiway/apron)
- **landing:** 4.0 jednostek/tick (szybki ruch po pasie podczas lądowania)
- **departing:** 4.0 jednostek/tick (szybki ruch po pasie podczas startu)
- **holding:** 0.0 jednostek/tick (bez ruchu podczas oczekiwania)
- **at_stand:** 0.0 jednostek/tick (bez ruchu na stanowisku)

---

## Diagram Flow

```
ARRIVAL:
waiting_landing → landing → taxiing_to_exit → at_exit → taxiing_to_stand → at_stand
     ↓              ↓            ↓              ↓              ↓              ↓
  [kolejka]    [ruch po]    [ruch do]     [oczekuje]    [ruch do]     [obsługa]
              [pasie]      [wyjścia]     [taxiway+      [stanowiska]  [10 ticków]
                                        apron+stand]

DEPARTURE:
at_stand → pushback_pending → pushback → waiting_departure → departing → [usunięcie]
    ↓            ↓               ↓              ↓                ↓
[obsługa]   [oczekuje]      [ruch do]      [kolejka]       [ruch po]
[10 ticków] [apron+taxi+    [wejścia]     [na pas]        [pasie]
            runway_entry]    [na pas]
```

---

## Uwagi Implementacyjne

1. **Brak rezerwacji węzłów podczas ruchu:** W `_move_along_path()` nie ma rezerwacji węzłów/krawędzi - samolot po prostu się porusza. Rezerwacje są tylko dla całych sekcji (`request_airport_section`).

2. **Brak sprawdzania konfliktów podczas ruchu:** `_move_along_path()` nie sprawdza czy segment jest zajęty - zakłada że rezerwacje z poprzednich stanów są wystarczające.

3. **RunwayController zarządza kolejką:** To `RunwayController` decyduje kiedy samolot może wejść na pas (dla lądowania i startu).

4. **Wyznaczanie ścieżki:** Ścieżka jest wyznaczana dynamicznie w `_move_along_path()` jeśli `path` jest puste, używając `find_shortest_path()`.
