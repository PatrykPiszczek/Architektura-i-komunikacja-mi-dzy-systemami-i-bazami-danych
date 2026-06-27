# SpendSync

Offline-first aplikacja do śledzenia wydatków osobistych. Składa się z serwera REST API (FastAPI + PostgreSQL) oraz aplikacji webowej PWA (vanilla JS), która działa również bez połączenia z internetem i synchronizuje dane z serwerem po odzyskaniu sieci.

**Autorzy:** Maciej Ciężarek 52655, Patryk Piszczek 52767

## Pomysł

Użytkownik zapisuje swoje wydatki (kwota, waluta, kategoria, opis, data), a aplikacja pokazuje sumę wydatków w bieżącym miesiącu, statystyki (wykres kołowy wydatków wg kategorii oraz słupkowy z ostatnich 6 miesięcy) i postęp wykonania budżetów. Kluczową cechą jest tryb offline: wydatki można dodawać, edytować i usuwać bez internetu — są zapisywane w lokalnej bazie w przeglądarce (IndexedDB), a następnie synchronizowane z serwerem, gdy połączenie wróci. W przypadku równoległej edycji tego samego rekordu na dwóch urządzeniach serwer rozwiązuje konflikt strategią last-write-wins.

Dodatkowo aplikacja korzysta z publicznego API Narodowego Banku Polskiego do przeliczania wydatków w walutach obcych (EUR, USD, GBP) na złotówki.

## Stos technologiczny

| Warstwa | Technologia |
| --- | --- |
| Serwer / API | Python 3.11, FastAPI, Uvicorn |
| ORM / baza | SQLAlchemy 2.0, PostgreSQL 16 |
| Uwierzytelnianie | JWT (HS256), OAuth2 password flow, passlib + bcrypt |
| Walidacja | Pydantic v2 |
| Frontend | HTML, CSS, vanilla JavaScript (bez frameworka), PWA |
| Lokalna baza offline | IndexedDB |
| Tryb offline aplikacji | Service Worker (cache powłoki) |
| Publiczne API | api.nbp.pl (kursy walut) |
| Konteneryzacja | Docker, Docker Compose, nginx |
| Testy | pytest (26 testów) |

## Uruchomienie (Docker)

Wymagany Docker i Docker Compose.

```bash
docker compose up --build
```

Po zbudowaniu:

- Aplikacja webowa: <http://localhost:8080>
- Dokumentacja API (Swagger UI): <http://localhost:8000/docs>
- Dokumentacja API (ReDoc): <http://localhost:8000/redoc>

Załadowanie danych demonstracyjnych:

```bash
docker compose exec backend python -m app.seed
```

Konto demo po załadowaniu seeda:

```
email:  demo@spendsync.pl
hasło:  demo1234
```

## Uruchomienie bez Dockera (lokalnie)

Backend (domyślnie użyje PostgreSQL; do szybkiego startu można wskazać SQLite przez zmienną środowiskową):

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="sqlite+pysqlite:///./spendsync.db"
export JWT_SECRET="dev-secret"
python -m app.seed                       # opcjonalnie: dane demo
uvicorn app.main:app --reload
```

Frontend to statyczne pliki. Najprościej:

```bash
cd frontend
python -m http.server 8080
```

Gdy frontend działa na innym porcie niż backend, ustaw w konsoli przeglądarki bazę API przed odświeżeniem, np.:

```js
window.SPENDSYNC_API = "http://localhost:8000";
```

W wariancie Docker nginx serwuje frontend i przekierowuje `/api/` do backendu, dzięki czemu wszystko działa same-origin (Service Worker i brak problemów z CORS).

## Testy

```bash
cd backend
pip install -r requirements.txt
pytest
```

Testy używają bazy SQLite, więc nie wymagają działającego PostgreSQL.

## Struktura projektu

```
spendsync/
├── docker-compose.yml
├── README.md
├── docs/
│   ├── API.md            opis endpointów z przykładami
│   ├── DATABASE.md       schemat bazy danych
│   └── AI_USAGE.md       informacja o wykorzystaniu AI
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py       aplikacja FastAPI, montaż routerów
│   │   ├── config.py     konfiguracja (zmienne środowiskowe)
│   │   ├── database.py   silnik i sesja SQLAlchemy
│   │   ├── models.py     modele ORM (User, Category, Expense, Budget)
│   │   ├── schemas.py    modele Pydantic (walidacja wejścia/wyjścia)
│   │   ├── auth.py       hashowanie haseł i tokeny JWT
│   │   ├── deps.py       zależność pobierająca zalogowanego użytkownika
│   │   ├── errors.py     spójna obsługa błędów
│   │   ├── seed.py       dane demonstracyjne
│   │   └── routers/      auth, categories, expenses, budgets, sync, rates
│   └── tests/            testy pytest
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── index.html
    ├── manifest.json
    ├── sw.js             Service Worker
    ├── css/style.css
    └── js/
        ├── api.js        klient HTTP + token
        ├── db.js         warstwa IndexedDB
        ├── auth.js       logowanie/rejestracja
        ├── sync.js       silnik synchronizacji
        └── app.js        logika i widoki aplikacji
```

## Podział zadań w zespole

| Obszar | Osoba |
| --- | --- |
| Backend, REST API, model bazy, uwierzytelnianie JWT, testy | Maciej Ciężarek 52655, Patryk Piszczek 52767
| Frontend PWA, IndexedDB, Service Worker, silnik synchronizacji | Maciej Ciężarek 52655, Patryk Piszczek 52767
| Dokumentacja, Docker, integracja | Maciej Ciężarek 52655, Patryk Piszczek 52767

## Pokrycie wymagań projektu

| Wymaganie | Gdzie zrealizowane |
| --- | --- |
| Serwer | FastAPI/Uvicorn (`backend/app/main.py`) |
| REST API | routery w `backend/app/routers/` |
| Integracja z bazą | SQLAlchemy + PostgreSQL (`database.py`, `models.py`) |
| Operacje CRUD | wydatki, kategorie, budżety |
| Kilka opcji wyszukiwania | `GET /expenses` (kategoria, zakres dat, zakres kwot, tekst) |
| Uwierzytelnianie | JWT (`auth.py`, `deps.py`, router `auth`) |
| Obsługa błędów | `errors.py` + spójne kody odpowiedzi |
| Aplikacja webowa | PWA w `frontend/` |
| Korzystanie z API | pobieranie i wyświetlanie danych (sync pull, kategorie, budżety) |
| Lokalna baza offline | IndexedDB (`db.js`) |
| Synchronizacja danych | `sync.js` + endpointy `/sync/changes` i `/sync/push` |
| Dokumentacja | `README.md`, `docs/`, automatyczny Swagger UI |
| Publiczne API (kreatywność) | kursy walut NBP (`rates.py`) |

Szczegóły API: [docs/API.md](docs/API.md). Schemat bazy: [docs/DATABASE.md](docs/DATABASE.md).
"# Architektura-i-komunikacja-mi-dzy-systemami-i-bazami-danych" 
