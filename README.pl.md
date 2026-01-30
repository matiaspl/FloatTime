# FloatTime - Ontime Overlay Timer

**English documentation:** [README.md](README.md)

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
- `window_position` - Pozycja okna: `[x, y]` (przywracana przy starcie; reset do domyślnej, jeśli poza dostępnym obszarem ekranu)
- `locked` - Stan zablokowania okna (true/false)
- `addtime_affects_event_duration` - Gdy true, +/- 1 min zmienia tylko czas trwania bieżącego wydarzenia (bez addtime); gdy false, +/- 1 min dodaje/odejmuje czas od działającego timera (true/false)

Możesz edytować ten plik ręcznie lub użyć menu kontekstowego aplikacji.

## Funkcje

### Podstawowe
- **Always-on-top** - Timer zawsze pozostaje na wierzchu innych okien (na macOS przez natywny poziom okna NSWindow)
- **Lekka** - Zbudowana w Python + PyQt6 (bez Electrona)
- **Cross-platform** - Działa na Windows, macOS i Linux
- **Konfiguracja URL** - Wystarczy podać adres serwera Ontime
- **System tray** - Działa w tle z ikoną w zasobniku systemowym

### Interakcja z oknem
- **Przeciąganie** - Można przesuwać okno myszką
- **Zmiana rozmiaru** - Można skalować okno z wszystkich 4 rogów
- **Ochrona ekranu** - Okno jest ograniczane do dostępnej geometrii ekranu (nie wychodzi poza ekran; działa na wielu monitorach)
- **Zapamiętywanie pozycji** - Ostatnia pozycja okna jest zapisywana i przywracana przy starcie; jeśli poza aktualnym obszarem ekranu, pozycja jest resetowana do domyślnej
- **Inteligentny kursor** - Kursor automatycznie zmienia się przy najechaniu na rogi okna
- **Automatyczne skalowanie** - Tekst timera dopasowuje się do rozmiaru okna (binarne wyszukiwanie optymalnego rozmiaru czcionki)
- **HiDPI** - Układ i czcionki odświeżają się przy przeniesieniu okna między ekranami o różnej DPI
- **Windows: bez przejmowania fokusu** - Kliknięcie w overlay nie przejmuje fokusu z innych aplikacji (np. PowerPoint pozostaje aktywny)

### Sterowanie timerem (nakładki po najechaniu)
- **Górna krawędź** - Przyciski **−1** i **+1** (odejmij/dodaj minutę), wyśrodkowane
- **Dolna krawędź** - **‹ Poprzednie**, **▶ Start**, **⏸ Pause**, **↻ Restart**, **› Następne** (poprzednie/następne wydarzenie, start, pauza, restart, następne)
- Obie grupy pojawiają się po najechaniu myszką na okno
- **Następne** i **Poprzednie** nie zawijają (wyłączone przy ostatnim/pierwszym wydarzeniu)

### Wyświetlanie
- **Tryby wyświetlania** - Przełączanie między timerem Ontime a zegarem systemowym
- **Obsługa typów timerów** - Automatyczne dostosowanie do typów: `count up`, `count down`, `clock`, `none`
- **Stan bez wydarzenia** - Gdy nie ma załadowanego wydarzenia, wyświetla `--:--` (przyciemnione) zamiast ostatniej wartości timera
- **Kolory progów** - Dynamiczna zmiana koloru tekstu:
  - **Biały** - Normalny stan
  - **Pomarańczowy** (`#FFA528`) - Próg ostrzegawczy (warning)
  - **Czerwony** (`#FA5656`) - Próg niebezpieczeństwa (danger/overtime)
- **Przezroczyste tło** - Opcja wyłączenia tła dla całkowicie przezroczystego okna
- **Własna czcionka** - Timer i zegar używają Iosevka Fixed Curly z katalogu `fonts/` (fallback: Arial)
- **Wyśrodkowanie timera** - Tekst timera jest wyśrodkowany (całkowite sekundy; countdown używa ceiling, żeby nie pomijać pierwszej sekundy)

### Konfiguracja i zapis
- **Zapis ustawień** - Aplikacja zapisuje: URL serwera, rozmiar okna, pozycję okna, tryb wyświetlania, widoczność tła, stan blokady, opcję „+/- 1 zmienia też długość wydarzenia”
- **Skróty klawiszowe**:
  - `Ctrl+Q` / `Ctrl+W` - Zamknij aplikację
  - `Escape` - Ukryj okno
  - **Podwójne kliknięcie** - Przeładuj bieżące wydarzenie i start (nie ukrywa okna)

## Wymagania

- Python 3.9 lub nowszy
- Serwer Ontime działający lokalnie lub zdalnie
- **macOS:** opcjonalnie `pyobjc-framework-Cocoa` dla poprawnego always-on-top (zainstaluj: `pip install pyobjc-framework-Cocoa`)

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
- **Lock in Place** - Zablokuj pozycję (wyłącz przeciąganie i zmianę rozmiaru)
- **Show Clock / Show Timer** - Przełącz między timerem a zegarem systemowym
- **Reset Size** - Przywróć domyślny rozmiar okna
- **+/- 1 also change event length** - Gdy zaznaczone, +/- 1 min zmienia tylko czas trwania bieżącego wydarzenia (bez addtime)
- **Timer** (podmenu) - Poprzednie wydarzenie, Następne wydarzenie, Start, Pause, Restart, +1 min, −1 min, Blink, Blackout
- **Quit** - Zamknij aplikację

## Kompilacja do pliku wykonywalnego

Skrypt budowania tworzy izolowane środowisko `.build_venv`, instaluje tam zależności i uruchamia PyInstaller, aby nie zaśmiecać Twojego środowiska Pythona.

```bash
python build.py
```

Wynik w katalogu `dist/floattime/` (tryb `--onedir`). Na macOS: `dist/floattime/floattime.app` lub `dist/floattime/floattime`.

## Użycie

### Podstawowe operacje

1. **Uruchom aplikację** - Aplikacja pojawi się w system tray
2. **Skonfiguruj URL** - Jeśli jeszcze nie skonfigurowano, podaj adres serwera Ontime
3. **Timer automatycznie się aktualizuje** - Dane są pobierane przez WebSocket w czasie rzeczywistym
4. **Przesuwaj okno** - Kliknij i przeciągnij okno (gdy nie zablokowane), aby je przesunąć
5. **Zmień rozmiar** - Najedź na róg okna (kursor się zmieni) i przeciągnij, aby zmienić rozmiar
6. **Sterowanie timerem** - Najedź na okno; u góry pojawią się −1/+1, na dole Poprzednie/Start/Pause/Restart/Następne

### Zmiana rozmiaru okna

- Najedź myszką na którykolwiek z 4 rogów okna
- Kursor automatycznie zmieni się na odpowiedni kształt (↖↘ lub ↗↙)
- Kliknij i przeciągnij, aby zmienić rozmiar
- Tekst timera automatycznie dopasowuje rozmiar czcionki do okna (do ~98% dostępnego miejsca)

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
FloatTime/
├── src/
│   ├── main.py              # Główna aplikacja
│   ├── ontime_client.py     # Klient API Ontime (WebSocket)
│   ├── timer_widget.py      # Widget wyświetlający timer
│   ├── timer_controls.py    # Nakładki sterowania (góra: −1/+1, dół: prev/play/pause/restart/next)
│   ├── tray_manager.py      # Ikona i menu w zasobniku systemowym
│   ├── config.py            # Zarządzanie konfiguracją
│   ├── logger.py            # Logowanie (FLOATTIME_DEBUG)
│   └── ui/
│       └── config_dialog.py # Dialog konfiguracji
├── fonts/                   # Własna czcionka (Iosevka Fixed Curly)
├── hooks/                   # Hooks PyInstaller (np. PyQt6)
├── requirements.txt         # Zależności
├── build.py                 # Skrypt kompilacji (venv + PyInstaller)
├── run.py                   # Skrypt uruchomienia
├── README.md                # Dokumentacja (angielski)
└── README.pl.md             # Dokumentacja (polski)
```

## API Ontime

Aplikacja łączy się z serwerem Ontime WebSocketów.

### WebSocket

- **Endpoint:** `ws://<adres-serwera>/ws` (z skonfigurowanego `server_url`: zamiana `http` na `ws` + `/ws`).
- **Po połączeniu:** klient wysyła `{"tag": "poll"}` w celu pobrania danych startowych/runtime.
- **Wiadomości przychodzące:** JSON z polami `tag` lub `type` i `payload`; aplikacja traktuje `payload` (lub całą wiadomość) jako dane Ontime. Aktualizacje granularne (`type`: `ontime-eventNow`, `ontime-timer` itd.) są rozpakowywane.
- **Sterowanie (wysyłane):**
  - `{"tag": "start"}` – start załadowanego wydarzenia
  - `{"tag": "pause"}` – pauza
  - `{"tag": "reload"}` – przeładowanie/restart bieżącego wydarzenia
  - `{"tag": "load", "payload": "next"}` – załaduj następne wydarzenie (bez zawijania przy ostatnim)
  - `{"tag": "load", "payload": "previous"}` – załaduj poprzednie wydarzenie
  - `{"tag": "addtime", "payload": {"add": ms}}` – dodaj czas (np. 60000 = +1 min)
  - `{"tag": "addtime", "payload": {"remove": ms}}` – odejmij czas (np. 60000 = −1 min)
  - `{"tag": "change", "payload": {"<event-id>": {"duration": ms}}}` – zmiana czasu trwania bieżącego wydarzenia (gdy włączone „+/- 1 zmienia też długość wydarzenia”)
  - `{"tag": "message", "payload": {"timer": {"blink": true/false}}}` – blink
  - `{"tag": "message", "payload": {"timer": {"blackout": true/false}}}` – blackout

### Format danych (parsowanie odpowiedzi serwera)

Aplikacja parsuje JSON w stylu Ontime:

- **Na górnym poziomie lub zagnieżdżone:** `timer` (obiekt lub wartość), `timerType`, `eventNow` / `currentEvent`, `eventNext` / `nextEvent`, `rundown`, `status`, `running`.
- **Rundown:** `selectedEventIndex`, `numEvents` – używane do włączania/wyłączania następnego i poprzedniego (bez zawijania).
- **Obiekt timera:** `current`, `remaining`, `elapsed`, `playback`, `state`, `running`, `timerType`, `timeWarning`, `timeDanger`, `duration`.
- **Wydarzenie:** `id`, `title`, `timerType`, `timeWarning`, `timeDanger`, `duration`, `timeStart`.

## Debugowanie

Aby włączyć szczegółowe logowanie, ustaw zmienną środowiskową:

```bash
export FLOATTIME_DEBUG=true   # Linux/macOS
set FLOATTIME_DEBUG=true      # Windows (cmd)
```

Następnie uruchom aplikację. Logi pojawią się w konsoli.

## Rozwiązywanie problemów

### Timer nie aktualizuje się
- Sprawdź, czy serwer Ontime działa i jest dostępny pod podanym adresem
- Sprawdź logi aplikacji (ustaw `FLOATTIME_DEBUG=true`)
- Upewnij się, że port nie jest zablokowany przez firewall

### Okno nie jest widoczne
- Sprawdź system tray - aplikacja może być ukryta
- Kliknij prawym przyciskiem na ikonę w tray i wybierz "Show"

### Always-on-top nie działa na macOS
- Zainstaluj: `pip install pyobjc-framework-Cocoa`
- Upewnij się, że "Always on Top" jest włączone w menu

### Kolory nie zmieniają się
- Upewnij się, że w Ontime są ustawione progi `timeWarning` i `timeDanger` dla wydarzenia
- Sprawdź, czy typ timera jest poprawnie wykrywany (włącz `FLOATTIME_DEBUG=true`)

## Licencja

GNU GPL — szczegóły w pliku [LICENSE.md](LICENSE.md).
