# Reguły Symulacji Lotniska

## 1. Ogólne Zasady

### 1.1 Reprezentacja Lotniska

- Lotnisko reprezentowane jako graf nieskierowany (`Graph`) i skierowany (`DiGraph`)
- Węzły reprezentują punkty lotniska (pasy, stanowiska, łączniki)
- Krawędzie reprezentują połączenia między punktami (pasy, taxiway, stand_link)
- **Wszystkie krawędzie są dwukierunkowe** (nieskierowane)

### 1.2 Jednostka Czasu

- Symulacja działa w krokach (ticks)
- 1 tick = 1 jednostka czasu symulacji
- Czas rzeczywisty zależy od konfiguracji prędkości

---

## 2. Stany Samolotów

### 2.1 Stany dla Samolotów Przybywających (Arrival)

1. **waiting_landing** - Oczekiwanie w powietrzu na zgodę ATC
2. **landing** - Lądowanie na pasie startowym
3. **taxiing_to_exit** - Taxi do wyjścia z pasa
4. **at_exit** - Na wyjściu z pasa, oczekiwanie na taxiway/apron
5. **taxiing_to_stand** - Taxi do stanowiska postojowego
6. **at_stand** - Na stanowisku, obsługa

### 2.2 Stany dla Samolotów Odlatujących (Departure)

1. **at_stand** - Na stanowisku, obsługa
2. **pushback_pending** - Oczekiwanie na pushback (apron + taxiway + runway_entry)
3. **pushback** - Pushback (wypychanie) z stanowiska
4. **waiting_departure** - Oczekiwanie na zgodę ATC do startu
5. **departing** - Start z pasa startowego

---

## 3. Rezerwacje Segmentów

### 3.1 Zasady Rezerwacji

- **Węzły:** Tylko jeden samolot na węźle w danym czasie (pojemność = 1)
- **Krawędzie:** Pojemność zależy od atrybutu `capacity` (domyślnie 1)
- **Zasada "first-come, first-served":** Brak negocjacji konfliktów
- Jeśli rezerwacja się nie powiedzie, samolot czeka i próbuje ponownie w następnym kroku

### 3.2 Rezerwacje Sekcji Lotniska

Metoda `request_airport_section()` rezerwuje całe sekcje:

- **"runway"** - Wszystkie krawędzie typu `runway`
- **"taxiway"** - Wszystkie krawędzie typu `taxiway`
- **"taxiway_inbound"** - Jedna krawędź typu `runway_entry` (pierwsza dostępna)
- **"taxiway_outbound"** - Jedna krawędź typu `runway_exit` (pierwsza dostępna)
- **"apron"** - Wszystkie krawędzie typu `stand_link`

### 3.3 Kiedy Rezerwacje Są Wykonywane

**Przed lądowaniem:**

- `taxiway_outbound` (wyjście z pasa)
- `runway` (cały pas)

**Przed taxi do stanowiska:**

- `taxiway` (wszystkie taxiway)
- `apron` (wszystkie stand_link)
- Wybór wolnego stanowiska

**Przed pushbackiem:**

- `apron` (wszystkie stand_link)
- `taxiway` (wszystkie taxiway)
- `runway_entry` (wejście na pas)

**Przed startem:**

- `runway` (cały pas)

### 3.4 Kiedy Rezerwacje Są Zwalniane

- Po dotarciu do celu (gdy `current_node == target_node`)
- Automatycznie przy przejściu do następnego stanu
- Przed usunięciem samolotu z symulacji

---

## 4. Kontrola Ruchu Lotniczego (ATC) (NOT IMPLEMENTED)

### 4.1 Separacje Czasowe (w sekundach)

- **T-T (Takeoff-Takeoff):** 60s
- **L-L (Landing-Landing):** 70s
- **T-L (Takeoff-Landing):** 90s
- **L-T (Landing-Takeoff):** 90s

### 4.2 Czasy Zajęcia Pasa

- **Line-up (wjazd na pas przed startem):** 20s
- **Takeoff roll (rozbieg do startu):** 35s
- **Landing roll (dojazd po lądowaniu):** 40s
- **Buffer po wyjeździe z pasa:** 15s

### 4.3 Blokada Pasa

- Pas jest blokowany od momentu `line-up` / `takeoff` / `landing` do momentu `runway_lock_until`
- `runway_lock_until = max(obecny_lock, czas_operacji + czas_zajęcia + bufor)`

### 4.4 Kolejka Pasa Startowego

- Jedna kolejka (`runway_queue`) dla lądowań i startów
- Priorytet dla samolotów przybywających (arrival)
- `RunwayController` decyduje o dostępie do pasa

---

## 5. Prędkości Ruchu

### 5.1 Prędkości (w jednostkach/tick)

- **taxiing:** 0.5 (wolny ruch po taxiway/apron)
- **landing:** 4.0 (szybki ruch po pasie podczas lądowania)
- **departing:** 4.0 (szybki ruch po pasie podczas startu)
- **holding:** 0.0 (bez ruchu podczas oczekiwania)
- **at_stand:** 0.0 (bez ruchu na stanowisku)

### 5.2 Minimalne Czasy Przejścia (w tickach)

- **taxiing:** 2 ticki
- **landing:** 1 tick
- **departing:** 1 tick
- **holding:** 1 tick
- **at_stand:** 1 tick

### 5.3 Obliczanie Czasu Ruchu

```
czas = max(1, int(odległość / prędkość))
czas_końcowy = max(czas, min_transit_time)
```

---

## 6. Czasy Operacji

### 6.1 Lądowanie

- **Czas lądowania:** 3 ticki (`max_landing_time`)
- Samolot porusza się po pasie podczas lądowania
- Po zakończeniu przechodzi do `taxiing_to_exit`

### 6.2 Obsługa na Stanowisku

- **Czas obsługi:** 10 ticków (`max_stand_time`)
- Samolot stoi na stanowisku bez ruchu
- Po zakończeniu przechodzi do `pushback_pending`

### 6.3 Pushback

- **Czas pushbacku:** 3 ticki (`default_pushback_time`)
- Samolot porusza się z stanowiska do punktu wejścia na pas
- Wymaga rezerwacji: apron + taxiway + runway_entry

### 6.4 Start

- **Czas startu:** 3 ticki (`max_departure_time`)
- Samolot porusza się po pasie podczas startu
- Po zakończeniu jest usuwany z symulacji

---

## 7. Miejsca Oczekiwania

### 7.1 waiting_landing

- **Lokalizacja:** W powietrzu (poza grafem, `current_node = None`)
- **Dlaczego czeka:** Oczekuje na zgodę ATC i dostępność pasa
- **Kolejka:** `runway_controller.runway_queue`
- **Warunek przejścia:** Zgoda ATC + rezerwacja `taxiway_outbound` + rezerwacja `runway`

### 7.2 at_exit

- **Lokalizacja:** Na węźle wyjścia z pasa
- **Dlaczego czeka:** Oczekuje na dostępność taxiway + apron + wolnego stanowiska
- **Warunek przejścia:** Rezerwacja `taxiway` + `apron` + `choose_stand()` = True

### 7.3 pushback_pending

- **Lokalizacja:** Na stanowisku
- **Dlaczego czeka:** Oczekuje na dostępność apron + taxiway + runway_entry
- **Warunek przejścia:** Rezerwacja `apron` + `taxiway` + `runway_entry` (przez `choose_runway_entry()`)

### 7.4 waiting_departure

- **Lokalizacja:** Na punkcie wejścia na pas (runway_entry)
- **Dlaczego czeka:** Oczekuje na zgodę ATC i dostępność pasa
- **Kolejka:** `runway_controller.runway_queue`
- **Warunek przejścia:** Zgoda ATC + rezerwacja `runway`

---

## 8. Wybór Trasy

### 8.1 Planowanie Trasy

- Używa algorytmu najkrótszej ścieżki (`find_shortest_path()`)
- Trasa jest wyznaczana dynamicznie gdy `path` jest puste
- Używa grafu skierowanego (`digraph`) do planowania

### 8.2 Wybór Stanowiska

- Wybiera losowo z dostępnych stanowisk
- Sprawdza które stanowiska są zajęte (`state == "at_stand"`)
- Jeśli wszystkie zajęte, zwraca `False` i czeka

### 8.3 Wybór Wyjścia z Pasa

- Wybiera pierwsze dostępne wyjście (`runway_exit`)
- Rezerwuje `taxiway_outbound` przed lądowaniem

### 8.4 Wybór Wejścia na Pas

- Wybiera wejście (`runway_entry`) pasujące do `runway_entry_node`
- Rezerwuje `runway_entry` przed pushbackiem

---

## 9. Interpolacja Ruchu

### 9.1 Płynny Ruch

- Pozycja samolotu jest interpolowana między węzłami
- `progress` od 0.0 (początek) do 1.0 (koniec)
- Pozycja aktualizowana w każdym kroku: `progress = elapsed_time / movement_duration`

### 9.2 Aktualizacja Pozycji

- `_update_movement()` aktualizuje pozycję w każdym kroku
- Gdy `progress >= 1.0`, ruch się kończy (`_finish_movement()`)
- Po zakończeniu ruchu zwalniane są rezerwacje poprzedniego węzła i krawędzi

---

## 10. Konfiguracja Pasa Startowego

### 10.1 Kierunek Wiatru

- Stały kierunek wiatru (`wind_direction = "07"` lub `"25"`)
- Określa aktywny pas startowy:
  - Wiatr "07" → pas RWY_07 (node_id = 1)
  - Wiatr "25" → pas RWY_25 (node_id = 2)

### 10.2 Aktywny Pas

- `active_runway` - węzeł pasa używany do lądowań
- `runway_entry_node` - węzeł wejścia na pas używany do startów
  - Wiatr "07" → entry node = 2 (RWY_25)
  - Wiatr "25" → entry node = 1 (RWY_07)

---

## 11. Typy Krawędzi

### 11.1 Klasyfikacja

- **runway** - Pas startowy (pojemność = 1, brak oczekiwania)
- **taxiway** - Droga kołowania (możliwe oczekiwanie na A/C/D/F)
- **runway_entry** - Wejście na pas (możliwe oczekiwanie)
- **runway_exit** - Wyjście z pasa (brak oczekiwania)
- **stand_link** - Połączenie do stanowiska (możliwe oczekiwanie)

### 11.2 Miejsca Oczekiwania (Holding)

- **Dozwolone:** stand_link, taxiway A/C/D/F, runway_entry
- **Zabronione:** runway, taxiway B, runway_exit

---

## 12. Zasady Priorytetów

### 12.1 Priorytety Operacji

- **Lądowanie ma priorytet** nad startem
- W kolejce pasa: arrival przed departure
- Brak negocjacji konfliktów - "first-come, first-served"

### 12.2 Priorytet Samolotu

- Każdy samolot ma `priority = 1` (domyślnie)
- Obecnie nie używane w logice konfliktów

---

## 13. Usuwanie Samolotów

### 13.1 Warunki Usunięcia

- Samolot jest usuwany z symulacji po zakończeniu startu
- Gdy `current_node == target_node` w stanie `departing`
- Przed usunięciem zwalniane są wszystkie rezerwacje

### 13.2 Czyszczenie

- Zwolnienie `blocked_edges`
- Zwolnienie węzła (`release_node`)
- Usunięcie z listy `model.airplanes`

---

## 14. Domyślne Parametry

### 14.1 Prędkości (DEFAULTS)

- `taxi_speed_straight_kts`: 20 węzłów
- `taxi_speed_turn_kts`: 10 węzłów
- `min_headway_m`: 100 metrów

### 14.2 Czasy Operacji (DEFAULTS)

- `pushback_time_s`: 90 sekund
- `runway_lineup_block_s`: 20 sekund
- `takeoff_roll_time_s`: 35 sekund
- `landing_roll_time_s`: 40 sekund
- `runway_buffer_after_exit_s`: 15 sekund

### 14.3 Separacje (DEFAULTS)

- `sep_TT_s`: 60 sekund
- `sep_LL_s`: 70 sekund
- `sep_TL_s`: 90 sekund
- `sep_LT_s`: 90 sekund

---

## 15. Uwagi Implementacyjne

### 15.1 Brak Rezerwacji Podczas Ruchu

- W `_move_along_path()` nie ma rezerwacji węzłów/krawędzi podczas ruchu
- Samolot zakłada że rezerwacje z poprzednich stanów są wystarczające
- Rezerwacje są wykonywane przed rozpoczęciem fazy ruchu

### 15.2 Brak Sprawdzania Konfliktów Podczas Ruchu

- `_move_along_path()` nie sprawdza czy segment jest zajęty
- Konflikty są rozwiązywane na poziomie rezerwacji przed ruchem

### 15.3 RunwayController Zarządza Kolejką

- `RunwayController` decyduje kiedy samolot może wejść na pas
- Sprawdza dostępność pasa i separacje ATC
- Ustawia stan samolotu na `landing` lub `departing`

### 15.4 Wyznaczanie Ścieżki

- Ścieżka jest wyznaczana dynamicznie w `_move_along_path()` jeśli `path` jest puste
- Używa `find_shortest_path()` z grafu skierowanego
- Ścieżka jest aktualizowana gdy samolot dociera do celu

---

## 16. Diagram Stanów

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

## 17. Wyjątki i Obsługa Błędów

### 17.1 Brak Ścieżki

- Jeśli `find_shortest_path()` zwraca pustą ścieżkę, samolot pozostaje w miejscu
- Próbuje ponownie w następnym kroku

### 17.2 Brak Dostępnych Stanowisk

- Jeśli wszystkie stanowiska są zajęte, samolot czeka w stanie `at_exit`
- Próbuje ponownie w następnym kroku

### 17.3 Nieudana Rezerwacja

- Jeśli rezerwacja się nie powiedzie, samolot pozostaje w stanie oczekiwania
- Próbuje ponownie w następnym kroku
- Zwalnia częściowe rezerwacje jeśli nie udało się zarezerwować wszystkich wymaganych sekcji

---

## 18. Rozszerzenia i Możliwości

### 18.1 Obecnie Niezaimplementowane

- Negocjacja konfliktów między samolotami
- Priorytety samolotów w konfliktach
- Alternatywne ścieżki przy konfliktach
- Dynamiczna zmiana kierunku wiatru
- Różne typy samolotów z różnymi parametrami
- Warunki pogodowe
- De-icing

### 18.2 Możliwe Rozszerzenia

- System priorytetów dla różnych typów operacji
- Negocjacja konfliktów z arbitrażem kontrolera
- Dynamiczne planowanie tras omijających konflikty
- Różne prędkości dla różnych typów samolotów
- System kolejek z pozycjami
- Statystyki i metryki wydajności
