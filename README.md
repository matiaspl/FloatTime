# FloatTime - Ontime Overlay Timer

Lekka aplikacja desktopowa wyświetlająca timer z Ontime w trybie always-on-top. Idealna do wyświetlania timera podczas prezentacji PowerPoint lub innych aplikacji.

## Konfiguracja

Aplikacja przechowuje konfigurację w pliku JSON w katalogu użytkownika:

**Windows:**
```
C:\Users\<username>\.floattime\config.json
```

**Linux/macOS:**
```
~/.floattime/config.json
```

Plik konfiguracyjny zawiera następujące ustawienia:
- `server_url` - URL serwera Ontime
- `display_mode` - Tryb wyświetlania: `"timer"` lub `"clock"`
- `background_visible` - Widoczność tła (true/false)
- `window_size` - Rozmiar okna: `[szerokość, wysokość]`
- `locked` - Stan zablokowania okna (true/false)

Możesz edytować ten plik ręcznie lub użyć menu kontekstowego aplikacji.

## Funkcje

### Podstawowe
- **Always-on-top** - Timer zawsze pozostaje na wierzchu innych okien
- **Lekka** - Zbudowana w Python + PyQt6 (bez Electrona)
- **Cross-platform** - Działa na Windows, macOS i Linux
- **Konfiguracja URL** - Wystarczy podać adres serwera Ontime
- **System tray** - Działa w tle z ikoną w zasobniku systemowym

### Interakcja z oknem
- **Przeciąganie** - Można przesuwać okno myszką
- **Zmiana rozmiaru** - Można skalować okno z wszystkich 4 rogów
- **Inteligentny kursor** - Kursor automatycznie zmienia się przy najechaniu na rogi okna
- **Automatyczne skalowanie** - Czcionki i layout automatycznie dostosowują się do rozmiaru okna

### Wyświetlanie
- **Tryby wyświetlania** - Przełączanie między timerem Ontime a zegarem systemowym
- **Obsługa typów timerów** - Automatyczne dostosowanie do typów: `count up`, `count down`, `clock`, `none`
- **Kolory progów** - Dynamiczna zmiana koloru tekstu:
  - **Biały** - Normalny stan
  - **Pomarańczowy** (`#FFA528`) - Próg ostrzegawczy (warning)
  - **Czerwony** (`#FA5656`) - Próg niebezpieczeństwa (danger/overtime)
- **Przezroczyste tło** - Opcja wyłączenia tła dla całkowicie przezroczystego okna

### Konfiguracja i zapis
- **Zapis ustawień** - Aplikacja zapisuje:
  - URL serwera Ontime
  - Rozmiar okna
  - Tryb wyświetlania (timer/clock)
  - Widoczność tła
- **Skróty klawiszowe**:
  - `Ctrl+Q` - Zamknij aplikację
  - `Ctrl+W` - Zamknij aplikację
  - `Escape` - Ukryj okno
  - **Podwójne kliknięcie** - Zamknij aplikację

## Wymagania

- Python 3.9 lub nowszy
- Serwer Ontime działający lokalnie lub zdalnie

## Instalacja

1. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

2. Uruchom aplikację:
```bash
python run.py
```

Lub bezpośrednio:
```bash
python src/main.py
```

## Konfiguracja

### Pierwsze uruchomienie

Przy pierwszym uruchomieniu aplikacja poprosi o podanie URL serwera Ontime (np. `http://localhost:4001`).

### Zmiana konfiguracji

Możesz zmienić konfigurację przez:
- **Menu system tray** - Kliknij prawym przyciskiem na ikonę w system tray i wybierz "Configure..."
- **Menu kontekstowe okna** - Kliknij prawym przyciskiem na okno timera

### Dostępne opcje

- **Configure...** - Zmiana URL serwera Ontime
- **Show/Hide** - Pokazuj/ukryj okno
- **Always on Top** - Przełącz tryb always-on-top
- **Show Background** - Przełącz widoczność tła (przezroczyste/nieprzezroczyste)
- **Show Clock** - Przełącz między timerem a zegarem systemowym
- **Quit** - Zamknij aplikację

## Kompilacja do pliku wykonywalnego

Aby utworzyć pojedynczy plik wykonywalny:

```bash
python build.py
```

Plik wykonywalny zostanie utworzony w katalogu `dist/`.

## Użycie

### Podstawowe operacje

1. **Uruchom aplikację** - Aplikacja pojawi się w system tray
2. **Skonfiguruj URL** - Jeśli jeszcze nie skonfigurowano, podaj adres serwera Ontime
3. **Timer automatycznie się aktualizuje** - Dane są pobierane przez WebSocket/Socket.IO w czasie rzeczywistym
4. **Przesuwaj okno** - Kliknij i przeciągnij okno, aby je przesunąć
5. **Zmień rozmiar** - Najedź na róg okna (kursor się zmieni) i przeciągnij, aby zmienić rozmiar

### Zmiana rozmiaru okna

- Najedź myszką na którykolwiek z 4 rogów okna
- Kursor automatycznie zmieni się na odpowiedni kształt (↖↘ lub ↗↙)
- Kliknij i przeciągnij, aby zmienić rozmiar
- Czcionki i layout automatycznie dostosują się do nowego rozmiaru

### Przełączanie trybów

- **Timer** - Wyświetla timer z Ontime (domyślnie)
- **Clock** - Wyświetla zegar systemowy
- Przełączanie przez menu system tray lub menu kontekstowe

### Kolory progów

Aplikacja automatycznie zmienia kolor tekstu timera w zależności od wartości:

- **Count Down Timer**:
  - Biały - Normalny stan (powyżej progów)
  - Pomarańczowy - Osiągnięto próg ostrzegawczy (`timeWarning`)
  - Czerwony - Osiągnięto próg niebezpieczeństwa (`timeDanger`) lub przekroczono czas (overtime)

- **Count Up Timer**:
  - Biały - Normalny stan (w ramach czasu)
  - Pomarańczowy - Przekroczono czas (`duration`)

## Struktura projektu

```
floattime/
├── src/
│   ├── main.py              # Główna aplikacja
│   ├── ontime_client.py     # Klient API Ontime (WebSocket/Socket.IO)
│   ├── timer_widget.py      # Widget wyświetlający timer
│   ├── config.py            # Zarządzanie konfiguracją
│   └── ui/
│       └── config_dialog.py # Dialog konfiguracji
├── requirements.txt         # Zależności
├── build.py                 # Skrypt kompilacji
├── run.py                   # Skrypt uruchomienia
└── README.md               # Ten plik
```

## API Ontime

Aplikacja łączy się z serwerem Ontime używając:

### WebSocket
- Endpoint: `ws://<server-url>/ws`
- Protokół: WebSocket z formatem wiadomości `{"tag": "...", "payload": ...}`
- Obsługiwane tagi: `poll`, `runtime-data`, `start`, `pause`, `stop`, `load`, `change`

### Socket.IO (fallback)
- Endpoint: `<server-url>` (Socket.IO client)
- Automatyczne wykrywanie i przełączanie między protokołami

### HTTP Polling (fallback)
- Endpointy: `/api/timer`, `/api/status`, `/api/ontime`
- Używane tylko gdy WebSocket/Socket.IO nie są dostępne

### Format danych

Aplikacja oczekuje danych w formacie Ontime:
- `timer` - Wartość timera w milisekundach
- `timerType` - Typ timera: `"count up"`, `"count down"`, `"clock"`, `"none"`
- `currentEvent` / `eventNow` - Aktualne wydarzenie z `timerType`, `timeWarning`, `timeDanger`, `duration`
- `timerDict` - Pełny obiekt timera z `current`, `elapsed`, `remaining`

## Debugowanie

Aby włączyć szczegółowe logowanie, zmień wartość `DEBUG_LOGGING = True` w:
- `src/main.py`
- `src/timer_widget.py`
- `src/ontime_client.py`

## Rozwiązywanie problemów

### Timer nie aktualizuje się
- Sprawdź, czy serwer Ontime działa i jest dostępny pod podanym adresem
- Sprawdź logi aplikacji (włącz `DEBUG_LOGGING`)
- Upewnij się, że port nie jest zablokowany przez firewall

### Okno nie jest widoczne
- Sprawdź system tray - aplikacja może być ukryta
- Kliknij prawym przyciskiem na ikonę w tray i wybierz "Show"

### Kolory nie zmieniają się
- Upewnij się, że w Ontime są ustawione progi `timeWarning` i `timeDanger` dla wydarzenia
- Sprawdź, czy typ timera jest poprawnie wykrywany (włącz `DEBUG_LOGGING`)

## Licencja

MIT
