# Dokumentacja API

Bazowy adres: `http://localhost:8000` (bezpośrednio) lub `http://localhost:8080/api` (przez nginx we frontendzie).

Wszystkie endpointy poza `/auth/register`, `/auth/login` i `/health` wymagają nagłówka:

```
Authorization: Bearer <token>
```

Interaktywna dokumentacja generowana automatycznie jest dostępna pod `/docs` (Swagger UI) oraz `/redoc`.

## Uwierzytelnianie

### POST /auth/register

Tworzy nowe konto.

Żądanie:

```json
{ "email": "ty@example.com", "password": "tajne123", "display_name": "Jan" }
```

Odpowiedź `201`:

```json
{ "id": 1, "email": "ty@example.com", "display_name": "Jan", "created_at": "2026-06-26T10:00:00Z" }
```

### POST /auth/login

Logowanie w formacie `application/x-www-form-urlencoded` (pola `username` = email, `password`). Taki format pozwala korzystać z przycisku „Authorize" w Swagger UI.

Odpowiedź `200`:

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

Błędne dane: `401`.

### GET /auth/me

Zwraca dane zalogowanego użytkownika.

## Kategorie

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| GET | `/categories` | lista kategorii użytkownika |
| POST | `/categories` | utworzenie kategorii |
| PUT | `/categories/{id}` | edycja |
| DELETE | `/categories/{id}` | usunięcie |

POST body:

```json
{ "name": "Jedzenie", "color": "#ef4444" }
```

## Wydatki

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| GET | `/expenses` | lista z filtrowaniem |
| POST | `/expenses` | utworzenie |
| GET | `/expenses/{id}` | pojedynczy wydatek |
| PUT | `/expenses/{id}` | edycja (podbija `version`) |
| DELETE | `/expenses/{id}` | usunięcie miękkie (`deleted = true`) |

Parametry wyszukiwania `GET /expenses` (wszystkie opcjonalne, można łączyć):

| Parametr | Znaczenie |
| --- | --- |
| `category_id` | filtr po kategorii |
| `date_from` | data od (`YYYY-MM-DD`) |
| `date_to` | data do |
| `min_amount` | kwota minimalna |
| `max_amount` | kwota maksymalna |
| `q` | fraza w opisie |

Przykład:

```
GET /expenses?category_id=2&date_from=2026-06-01&min_amount=10&q=bilet
```

POST body:

```json
{
  "amount": 24.50,
  "currency": "PLN",
  "description": "Lunch",
  "spent_at": "2026-06-26",
  "category_id": 2
}
```

Odpowiedź `201`:

```json
{
  "id": 10,
  "amount": 24.5,
  "currency": "PLN",
  "description": "Lunch",
  "spent_at": "2026-06-26",
  "category_id": 2,
  "version": 1,
  "deleted": false,
  "client_uuid": "1f3c...",
  "updated_at": "2026-06-26T10:05:00Z"
}
```

## Budżety

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| GET | `/budgets` | lista budżetów |
| GET | `/budgets/summary?period=YYYY-MM` | budżety z wyliczonym wydatkiem i pozostałą kwotą |
| POST | `/budgets` | utworzenie |
| PUT | `/budgets/{id}` | edycja |
| DELETE | `/budgets/{id}` | usunięcie |

`GET /budgets/summary` łączy dane z tabel `budgets`, `expenses` i `categories`:

```json
[
  {
    "id": 1,
    "period": "2026-06",
    "limit_amount": 600.0,
    "category_id": 1,
    "category_name": "Jedzenie",
    "spent": 180.8,
    "remaining": 419.2
  }
]
```

## Synchronizacja

### GET /sync/changes?since=&lt;timestamp&gt;

Zwraca rekordy zmienione po podanym czasie (pull). Bez parametru `since` zwraca wszystko. Używane przez klienta do pobrania zmian z serwera.

```json
{
  "server_time": "2026-06-26T10:10:00Z",
  "categories": [ ... ],
  "expenses": [ ... ],
  "budgets": [ ... ]
}
```

Klient zapisuje `server_time` i przekazuje je jako `since` przy następnej synchronizacji.

### POST /sync/push

Wysyła zmiany wykonane offline (push). Każda zmiana zawiera `client_uuid`, `base_version` (ostatnia znana wersja z serwera) oraz `updated_at` (czas lokalnej modyfikacji).

```json
{
  "changes": [
    {
      "client_uuid": "1f3c...",
      "amount": 30.0,
      "currency": "PLN",
      "description": "Zakupy",
      "spent_at": "2026-06-26",
      "category_id": 1,
      "deleted": false,
      "base_version": 0,
      "updated_at": "2026-06-26T09:00:00Z"
    }
  ]
}
```

Odpowiedź zawiera autorytatywny stan każdego rekordu i status operacji:

```json
{
  "server_time": "2026-06-26T10:11:00Z",
  "results": [
    { "status": "created", "expense": { "id": 11, "version": 1, ... } }
  ]
}
```

Możliwe wartości `status`:

| Status | Znaczenie |
| --- | --- |
| `created` | utworzono nowy rekord (brak na serwerze) |
| `updated` | zaktualizowano (wersja klienta zgodna z serwerem) |
| `conflict_client_won` | konflikt rozwiązany na korzyść klienta (nowszy `updated_at`) |
| `conflict_server_won` | konflikt rozwiązany na korzyść serwera (starszy `updated_at`) |

Strategia rozwiązywania konfliktów: last-write-wins według `updated_at`.

## Kursy walut

### GET /rates?code=EUR

Proxy do publicznego API NBP. Dla `PLN` zwraca kurs 1.0 bez odpytywania serwisu.

```json
{ "code": "EUR", "rate": 4.32, "date": "2026-06-25", "source": "NBP" }
```

## Format błędów

Błąd walidacji (`422`):

```json
{
  "detail": "Validation failed",
  "errors": [ { "field": "body.amount", "message": "Input should be greater than 0" } ]
}
```

Pozostałe błędy zwracają `{ "detail": "..." }` z odpowiednim kodem HTTP (`401`, `404`, `409`).
