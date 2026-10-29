# Запуск Internet Pharmacy з нуля

Інструкція для Ubuntu/Linux з кореня репозиторію. Звичайний запуск використовує наявний Docker volume і базу `internet_pharmacy`; він не видаляє дані. **Не використовуйте `docker compose down -v`, `docker volume rm` або `flush`.** Django-команда `migrate` вимкнена: структура БД управляється лише SQL-міграціями в `db/migrations/`.

## 1. Перейдіть у репозиторій

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy
```

Переконайтеся, що Docker і Compose доступні:

```bash
docker --version
docker compose version
```

Якщо Docker daemon зупинений:

```bash
sudo systemctl start docker
```

Якщо команда Docker повертає `permission denied`, виконуйте Docker-команди через `sudo` або налаштуйте доступ свого користувача до Docker і повторно увійдіть у систему.

## 2. Перевірте локальне налаштування `.env`

`.env` містить локальні паролі й не має додаватися до Git. На новій копії створіть його з прикладу лише один раз:

```bash
[ -f .env ] || cp .env.example .env
nano .env
```

Замініть значення-заповнювачі щонайменше для `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD` і `DJANGO_SECRET_KEY`. Згенерувати секрет Django можна так:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Збережіть його в `.env` як `DJANGO_SECRET_KEY`. Для локального запуску залиште `MYSQL_DATABASE=internet_pharmacy` і `MYSQL_PORT=3308`, якщо порт 3308 вільний. Якщо змінюєте `MYSQL_PORT`, використовуйте той самий порт і для перевірки/міграцій.

## 3. Запустіть MySQL

```bash
docker compose -f compose.yaml -f compose.backend.yaml up -d db
docker compose -f compose.yaml -f compose.backend.yaml ps
docker compose -f compose.yaml -f compose.backend.yaml logs --tail=50 db
```

У `ps` дочекайтеся стану `healthy`. Логи MySQL мають містити `ready for connections`.

Якщо порт зайнятий, перевірте його власника:

```bash
sudo ss -ltnp | grep ':3308'
```

Зупиніть лише відомий процес, який займає цей порт, або задайте в `.env` інший вільний `MYSQL_PORT`, наприклад `3310`, а потім знову запустіть Compose.

## 4. Підготуйте інструмент SQL-міграцій

Цей крок потрібен для першого налаштування нової БД або коли ви переглянули й вирішили застосувати наявні pending SQL-міграції. Скрипт підключається до MySQL за параметрами `.env`, перевіряє контрольні суми та пропускає вже застосовані міграції.

```bash
python3 -m venv .venv
.venv/bin/pip install mysql-connector-python
.venv/bin/python db/scripts/migrate.py
.venv/bin/python db/scripts/verify_schema.py
```

Очікуваний результат перевірки схеми: `SCHEMA VERIFICATION: PASS`. Не запускайте `python manage.py migrate`, `makemigrations` або `flush`.

> На наявному навчальному volume каталог і дані вже підготовлені. Міграції не потрібно запускати при кожному старті; цей розділ потрібен для першої інсталяції чи після перегляду нових SQL-міграцій. Зовсім нова порожня БД після міграцій матиме схему, але не каталог навчальних даних.

## 5. Запустіть Backend і Worker

З кореня репозиторію:

```bash
sudo docker compose -f compose.yaml -f compose.backend.yaml up -d --build backend worker
sudo docker compose -f compose.yaml -f compose.backend.yaml ps
```

Перевірте стан API та відкрийте документацію:

```bash
curl --fail http://127.0.0.1:8000/api/health/
```

- Сайт API: <http://127.0.0.1:8000/api/>
- Swagger: <http://127.0.0.1:8000/api/docs/>
- OpenAPI: <http://127.0.0.1:8000/api/schema/>

Якщо сервіс не стартував, подивіться його логи:

```bash
docker compose -f compose.yaml -f compose.backend.yaml logs --tail=100 backend worker
```

## 6. Запустіть Frontend

Відкрийте **другий термінал** і виконайте:

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy
FRONTEND_PORT=4173 API_ORIGIN=http://127.0.0.1:8000 node apps/frontend/server.mjs
```

Тримайте цей термінал відкритим, поки працює сайт. Відкрийте у браузері:

<http://127.0.0.1:4173/#home>

Якщо код frontend змінено, достатньо оновити сторінку через **Ctrl+Shift+R**. Якщо сервер frontend зупинився, запустіть команду ще раз у терміналі.

## 7. Швидка перевірка всіх компонентів

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy
docker compose -f compose.yaml -f compose.backend.yaml ps
curl --fail http://127.0.0.1:8000/api/health/
curl --fail http://127.0.0.1:4173/
```

Очікується: `db` має бути `healthy`, `backend` — `healthy` або `running`, `worker` — `running`; обидва `curl` мають завершитися без помилки.

## 8. Як зупинити

У терміналі frontend натисніть **Ctrl+C**. У будь-якому терміналі можна зупинити серверні контейнери:

```bash
cd /home/petro/Documents/ChatGPT/online-pharmacy
docker compose -f compose.yaml -f compose.backend.yaml stop backend worker db
```

Зупинка контейнера не видаляє контейнер або дані. Щоб наступного разу знову запустити систему, повторіть розділи 3, 5 і 6. Для звичайного перезапуску Backend/Worker після змін у Python-коді:

```bash
docker compose -f compose.yaml -f compose.backend.yaml up -d --build backend worker
```

## Часті причини помилок

- **Docker permission denied:** скористайтеся `sudo` для Docker-команд або налаштуйте членство користувача в групі `docker` і повторно увійдіть.
- **`docker compose` невідома команда:** на системі не встановлений Docker Compose plugin; встановіть його для свого дистрибутива Docker.
- **Порт 3308 зайнятий:** перевірте `sudo ss -ltnp | grep ':3308'`, змініть `MYSQL_PORT` у `.env` на вільний і повторно створіть `db` через Compose.
- **Backend не підключається до БД:** переконайтеся, що Compose `db` у стані `healthy`, а ім’я бази та паролі у `.env` правильні. Усередині Compose Backend використовує `db:3306`; `MYSQL_PORT` — це порт для підключення з хоста.
- **Сайт відкривається, але API недоступне:** перевірте `curl --fail http://127.0.0.1:8000/api/health/` і логи `backend`.
- **Порожній каталог на новому Docker volume:** це нова порожня база. Не запускайте seed-скрипти навмання на основній БД; окремо перегляньте інструкції в [db/README.md](../db/README.md) та погоджений план даних.
