# Запуск Internet Pharmacy

Команди виконуйте з кореня проєкту. Потрібні Docker Compose та Node.js.

## 1. Backend і база даних

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml up --build -d
```

Якщо отримали `permission denied`, додайте `sudo` перед командою.

## 2. Обидва сайти

```bash
node apps/start-portals.mjs
```

| Сервіс                              | Адреса                          |
| ----------------------------------- | ------------------------------- |
| Магазин                             | http://localhost:4173           |
| Кабінет працівника / адміністратора | http://localhost:4174           |
| Документація API                    | http://localhost:8000/api/docs/ |

**Початковий адміністратор:** логін `admin`, пароль `admin`.
Він створюється під час запуску оновленого Backend лише за відсутності ADMIN у базі. Щоб змінити пароль уже створеного акаунта `admin`, виконайте:

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml exec backend python manage.py set_coursework_admin_password
```

Для окремого запуску сайтів використовуйте різні термінали:

```bash
node apps/customer-web/server.mjs
node apps/management-web/server.mjs
```

## Перезапуск після змін

Якщо додалася SQL-міграція, спочатку застосуйте її до поточної бази:

```bash
.venv/bin/python db/scripts/migrate.py
```

Після змін Backend перебудуйте й перезапустіть backend та worker:

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml up --build -d backend worker
```

Після змін у порталах зупиніть їх у терміналі через `Ctrl+C` і запустіть знову:

```bash
node apps/start-portals.mjs
```

Якщо портали запущені через Compose, перебудуйте їх так:

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml -f compose.portals.yaml up --build -d customer-web management-web
```

Перевірити стан і журнали:

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml ps
sudo docker compose -f compose.yaml -f compose.backend.yaml logs --tail=100 backend worker
curl --fail http://127.0.0.1:8000/api/health/
```

## Зупинка

Сайти: `Ctrl+C` у їхньому терміналі.

```bash
docker compose -f compose.yaml -f compose.backend.yaml stop
```

Дані MySQL зберігаються. Не додавайте `down -v` — це видалить том із базою.

## Лише для першого налаштування

Якщо `.env` ще немає, скопіюйте `.env.example` у `.env` і задайте `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `DJANGO_SECRET_KEY`. Для нової порожньої БД виконайте підготовку схеми за [інструкцією Backend](backend/README.md). Для поточної навчальної бази повторна підготовка не потрібна.

Створення працівників і сценарій демонстрації: [окрема інструкція](portals/DEMONSTRATION.md).
