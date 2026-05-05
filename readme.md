
# OnyxSky LMS

Платформа для автоматической и ручной проверки заданий по программированию.  
Поддерживает Python, C++, JavaScript, Java и тесты с вариантами ответов.  
Построена на Flask, Celery, Docker, PostgreSQL и Redis.

## Основные возможности

- **3 типа заданий**  
  Ручная проверка, автоматическая (скрипты), тесты с выбором ответов.

- **Автоматическая проверка кода**  
  Код студента запускается в изолированном Docker-контейнере.  
  Проверочные скрипты пишутся администратором на Python и могут тестировать любой язык.

- **Мультиязычность**  
  Одно задание может приниматься на Python, C++, JavaScript или Java.  
  Студент выбирает язык в редакторе, и его решение запускается нужным компилятором.

- **Редактор кода**  
  Встроенный CodeMirror с подсветкой синтаксиса и автодополнением.

- **Тесты**  
  Одиночный / множественный выбор, открытый ответ.  
  Баллы за вопросы настраиваются, перепроверка — одной кнопкой.

- **Группы и приглашения**  
  Администратор создаёт группы, генерирует ссылки-приглашения.  
  Студенты могут вступить по ссылке, задания видны только участникам группы.

- **Дедлайны и попытки**  
  Каждому заданию можно задать дату сдачи и максимальное число попыток.

- **Личный кабинет**  
  Статистика, баллы, просмотр своих решений с подсветкой кода и кнопкой копирования.

- **Админ-панель**  
  Управление заданиями, скриптами, группами, проверка решений (ручная и автоматическая).

- **OAuth-авторизация**  
  Вход через Google и GitHub.

- **Безопасная изоляция**  
  Студенческий код компилируется и выполняется в Docker-контейнере с ограниченной памятью, без сети, с правами обычного пользователя.

- **Кеширование и асинхронность**  
  Redis используется для кеширования страниц и как брокер очередей Celery.

## Технологический стек

- **Backend:** Python 3.14, Flask, Gunicorn
- **База данных:** PostgreSQL
- **Очереди задач:** Celery + Redis
- **Контейнеризация:** Docker
- **Прокси-сервер:** Nginx
- **Аутентификация:** Flask-Login, OAuth (Google, GitHub)
- **Frontend:** Bootstrap 5, CodeMirror, Jinja2

## Установка и запуск

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/NaoTomori/LMSProject.git
cd LMSProject
```

### 2. Установите зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройте переменные окружения

Создайте файл `.env` в корне проекта:

```
SECRET_KEY=очень-длинный-случайный-ключ
DATABASE_URL=postgresql://lms_user:пароль@localhost:5432/lms_db
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@lms.local
ADMIN_PASSWORD=надёжный_пароль
BASE_URL=http://localhost:5555   # при разработке
```

Для почтовой верификации:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=пароль_приложения
```

### 4. Настройте PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER lms_user WITH PASSWORD 'пароль';"
sudo -u postgres psql -c "CREATE DATABASE lms_db OWNER lms_user;"
```

### 5. Создайте таблицы и администратора

```bash
flask db init
flask db migrate -m "Initial"
flask db upgrade
flask create-admin
```

### 6. Соберите Docker-образ для песочницы

```bash
cd sandbox
docker build -t lms-sandbox .
cd ..
```

### 7. Запустите сервер (для разработки)

```bash
python run.py
```

Для продакшена используйте Gunicorn и systemd (примеры unit-файлов в репозитории).

## Ссылка для быстрого входа администратора

```bash
flask gen-admin-login
```

Выдаст постоянную ссылку, действительную пока не изменится `SECRET_KEY`.

## Структура проекта

```
LMSProject/
├── app/
│   ├── routes/          # маршруты (auth, main, admin, cabinet)
│   ├── templates/       # Jinja2 шаблоны
│   ├── static/          # CSS, JS, изображения
│   ├── models.py        # модели SQLAlchemy
│   ├── utils.py         # генерация токенов, отправка писем, Docker
│   └── tasks.py         # задачи Celery
├── sandbox/             # Dockerfile для изолированной проверки
├── migrations/          # миграции Alembic
├── run.py               # точка входа Flask
├── wsgi.py              # точка входа Gunicorn
└── requirements.txt
```

## Лицензия

GPL-3.0 license
