# Schemat bazy danych

Baza zawiera cztery tabele: `users`, `categories`, `expenses`, `budgets`. Silnikiem produkcyjnym jest PostgreSQL; testy korzystają z SQLite (modele są niezależne od dialektu).

## Relacje

```
users (1) ──< (N) categories
users (1) ──< (N) expenses
users (1) ──< (N) budgets
categories (1) ──< (N) expenses
categories (1) ──< (N) budgets
```

Każdy użytkownik ma własne kategorie, wydatki i budżety. Wydatek i budżet mogą wskazywać kategorię (opcjonalnie).

## users

| Kolumna | Typ | Uwagi |
| --- | --- | --- |
| id | integer | PK |
| email | varchar(255) | unikalny, indeks |
| password_hash | varchar(255) | hash bcrypt |
| display_name | varchar(120) | |
| created_at | timestamptz | ustawiane automatycznie |

## categories

| Kolumna | Typ | Uwagi |
| --- | --- | --- |
| id | integer | PK |
| user_id | integer | FK → users.id |
| name | varchar(80) | |
| color | varchar(9) | kolor w formacie hex |
| created_at | timestamptz | |
| updated_at | timestamptz | aktualizowane przy zmianie |

## expenses

| Kolumna | Typ | Uwagi |
| --- | --- | --- |
| id | integer | PK |
| user_id | integer | FK → users.id |
| category_id | integer | FK → categories.id, dopuszcza NULL |
| amount | numeric(12,2) | kwota |
| currency | varchar(3) | domyślnie PLN |
| description | varchar(255) | |
| spent_at | date | data wydatku |
| version | integer | numer wersji rekordu (synchronizacja) |
| deleted | boolean | usunięcie miękkie (tombstone) |
| client_uuid | varchar(36) | identyfikator nadawany przez klienta |
| created_at | timestamptz | |
| updated_at | timestamptz | aktualizowane przy zmianie |

Cztery ostatnie pola merytoryczne (`version`, `deleted`, `client_uuid`, `updated_at`) obsługują synchronizację offline:

- `client_uuid` jest generowany przez aplikację w momencie utworzenia wydatku (również offline). Dzięki temu serwer rozpoznaje, czy przychodzący rekord jest nowy, czy aktualizacją istniejącego — bez polegania na identyfikatorze z serwera, którego rekord stworzony offline jeszcze nie ma.
- `version` rośnie przy każdej zmianie na serwerze. Klient wysyła ostatnią znaną wersję (`base_version`); różnica oznacza konflikt.
- `updated_at` służy do rozstrzygania konfliktów strategią last-write-wins.
- `deleted` pozwala synchronizować usunięcia (rekord nie znika fizycznie, więc pull przenosi informację o usunięciu na inne urządzenia).

## budgets

| Kolumna | Typ | Uwagi |
| --- | --- | --- |
| id | integer | PK |
| user_id | integer | FK → users.id |
| category_id | integer | FK → categories.id, dopuszcza NULL (budżet ogólny) |
| period | varchar(7) | miesiąc w formacie `YYYY-MM` |
| limit_amount | numeric(12,2) | limit wydatków |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Widok `GET /budgets/summary` łączy `budgets` z `expenses` (oraz `categories` dla nazwy), sumując wydatki danego miesiąca i wyliczając kwotę pozostałą.

## Tworzenie tabel

Tabele są tworzone automatycznie przy starcie aplikacji (`Base.metadata.create_all`). Dane demonstracyjne ładuje skrypt `python -m app.seed`.
