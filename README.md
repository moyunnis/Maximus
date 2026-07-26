<p align="center">
  <img src="./logo.png" alt="Maximus Logo" width="150" style="border-radius:50% !important;" />
</p>

<h1 align="center">Maximus — UserBot для мессенджера "Max"</h1>

<p align="center">
  <a href="https://github.com/moyunnis/Maximus/stars"><img src="https://img.shields.io/badge/dynamic/json?color=FFC107&style=for-the-badge&logo=github&label=Stars&query=%24.stars&url=https%3A%2F%2Fgithub.com%2Fapi%2Fv1%2Frepos%2Fmoyunni%2FMaximus" alt="Stars"></a>
  <a href="https://github.com/moyunnis/Maximus/src/branch/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-8BC34A?style=for-the-badge" alt="License"></a>
  <a href="https://t.me/moyunni_room"><img src="https://img.shields.io/badge/Telegram-Новости-blue?style=for-the-badge&logo=telegram" alt="Telegram Channel"></a>
</p>

<p align="center">
  ⚡️ Лучший UserBot для мессенджера <b>Max</b> с удобной системой модулей и легкостью.
  <br>
  Создан <a href="https://t.me/moyunnie">Moyunni</a> с ❤️
</p>

<p align="center">
  <img src="./banner.png" alt="Maximus Banner" width="100%" style="border-radius:5% !important;" />
</p>

---

## О проекте

**Maximus** — это новаторский UserBot для мессенджера Max, разработанный для автоматизации рутинных действий и расширения стандартного функционала. Это первый в своем роде юзербот для данной платформы, предлагающий пользователям непревзойденные возможности.

Проект работает на Python и использует библиотеку [PyMax (maxapi-python)](https://github.com/MaxApiTeam/PyMax) для взаимодействия с API мессенджера Max. Благодаря своей архитектуре, Maximus легко запускается как на VDS/VPS, так и на локальной машине, а его система плагинов обеспечивает простую кастомизацию и расширение.

---

## Ключевые возможности

- **Автоматизация:** Настраивайте автоматические ответы, команды и сценарии
- **Гибкая система модулей:** Расширяйте функционал с помощью готовых плагинов или создавайте свои
- **Поддержка чатов:** Стабильная работа в личных сообщениях и групповых чатах
- **Простая установка:** Готовые скрипты для быстрой установки на Windows и Linux
- **Удобная настройка:** Конфигурация через простые и понятные файлы
- **Markdown:** Поддержка форматирования текста (жирный, курсив, подчёркивание)
- **Медиа:** Отправка фото, файлов и видео

---

## Новости и поддержка

Все актуальные новости, обновления и полезную информацию о проекте вы найдете в нашем официальном Telegram-канале.

➡️ **Подписаться на канал:** [moyunni_room.t.me](https://t.me/moyunni_room)

---

## Требования

Перед установкой убедитесь, что у вас установлено:

| Требование | Минимальная версия | Как проверить |
|------------|-------------------|---------------|
| Python | 3.12+ | `python --version` |
| pip | Любая | `pip --version` |
| Git | Любая | `git --version` |

### Установка Python

<details>
<summary><b>Windows</b></summary>

1. Скачайте Python с официального сайта: https://www.python.org/downloads/
2. **Важно:** При установке обязательно поставьте галочку ✅ **"Add Python to PATH"**
3. Нажмите "Install Now"
4. После установки откройте PowerShell и проверьте: `python --version`

</details>

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip git -y
```

</details>

<details>
<summary><b>macOS</b></summary>

```bash
# Через Homebrew
brew install python@3.12 git
```

</details>

---

## Установка

### Windows

<details>
<summary><b>Ручная установка через PowerShell</b></summary>

Откройте PowerShell и выполните команды по очереди:

```powershell
# 1. Клонируем репозиторий
git clone https://github.com/moyunnis/Maximus.git

# 2. Переходим в папку проекта
cd Maximus

# 3. Создаём виртуальное окружение
python -m venv venv

# 4. Активируем виртуальное окружение
venv\Scripts\activate

# 5. Устанавливаем зависимости
pip install -r requirements.txt

# 6. Запускаем бота
python main.py
```

При первом запуске:
- Введите номер телефона в формате `+79001234567`
- Введите код подтверждения из мессенджера Max

</details>

---

### Linux

<details>
<summary><b>Ручная установка</b></summary>

```bash
# Всё в одной команде:
git clone https://github.com/moyunnis/Maximus.git && cd Maximus && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 main.py
```

**Или пошагово:**

```bash
# 1. Клонируем репозиторий
git clone https://github.com/moyunnis/Maximus.git

# 2. Переходим в папку проекта
cd Maximus

# 3. Создаём виртуальное окружение
python3 -m venv venv

# 4. Активируем виртуальное окружение
source venv/bin/activate

# 5. Устанавливаем зависимости
pip install -r requirements.txt

# 6. Запускаем бота
python3 main.py
```

</details>

---

## Быстрый запуск

После установки для запуска бота достаточно использовать стартовые скрипты:

**Windows:**
```powershell
# Просто дважды кликните по start.bat
# Или в PowerShell:
.\run.bat
```

**Linux:**
```bash
# Сделайте скрипт исполняемым (один раз):
chmod +x run.sh

# Запускайте:
./run.sh
```

---

## Автозапуск

<details>
<summary><b>Windows — через Планировщик задач</b></summary>

1. Откройте Планировщик задач (нажмите `Win+R`, введите `taskschd.msc`)
2. Нажмите **"Создать задачу..."** (не "Создать простую задачу")
3. На вкладке **"Общие"**:
   - Название: `Maximus`
   - Поставьте галочку "Выполнять с наивысшими правами"
4. На вкладке **"Триггеры"**:
   - Нажмите "Создать..."
   - Выберите "При входе в систему"
   - ОК
5. На вкладке **"Действия"**:
   - Нажмите "Создать..."
   - Действие: "Запуск программы"
   - Программа: путь к `run.bat` в папке Maximus
   - ОК
6. Сохраните задачу

</details>

<details>
<summary><b>Linux — через systemd (systemd хуйня, btw)</b></summary>

1. Отредактируйте файл сервиса (укажите ваш путь и пользователя):
   ```bash
   nano maximus.service
   ```
   
2. Скопируйте сервис в системную директорию:
   ```bash
   sudo cp maximus.service /etc/systemd/system/
   ```

3. Перезагрузите конфигурацию systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

4. Включите автозапуск:
   ```bash
   sudo systemctl enable maximus
   ```

5. Запустите сервис:
   ```bash
   sudo systemctl start maximus
   ```

6. Проверьте статус:
   ```bash
   sudo systemctl status maximus
   ```

</details>

---

## Структура проекта

```
ЕЕ СЪЕЛИ КРОКОДИЛЫ
```

---

## Встроенные команды

Прямо из коробки, без установки модулей (префикс по умолчанию — `.`):

| Команда | Что делает |
|---------|-----------|
| `.info` | Инфо о боте: аптайм, версия, кол-во модулей/команд, хост, Python, PyMax |
| `.help` | Список всех команд и модулей; `.help <модуль>` — подробнее |
| `.ping` | Задержка + аптайм |
| `.uptime` | Сколько работает юзербот |
| `.id` | ID чата, твой ID и (при реплае) ID автора/сообщения |
| `.calc <выражение>` | Безопасный калькулятор: `.calc (2 + 3) * 4` |
| `.whois [id]` | Инфо о пользователе (реплаем или по ID) |
| `.repeat <N> <текст>` | Повторить текст N раз |
| `.config` / `.configset` | Просмотр и изменение переменных модулей |
| `.load` / `.unload` / `.modules` | Управление модулями |
| `.reload` / `.update` / `.restart` | Перезагрузка модулей / обновление ядра / рестарт |
| `.backup` / `.loadbackup` | Бэкап и восстановление конфига и модулей |
| `.exportlog [N]` | Выгрузить последние N строк логов файлом |
| `.setprefix` / `.addalias` / `.remalias` | Префикс и алиасы команд |

---

## Создание модулей

Хотите создать свой модуль? ЗАЙДИТЕ В **[!!!ПОРТАЛ В РОБЛОКС!!!](mods/README.md)**.

Maximus использует библиотеку **[PyMax](https://github.com/MaxApiTeam/PyMax)** — вы можете использовать все её возможности в своих модулях!

### Быстрый пример модуля:

```python
# name: Мой модуль
# version: 1.0.0
# developer: Ваше имя
# id: my_module
# min-Maximus: 100

async def hello_command(api, message, args):
    """Простое приветствие."""
    await api.edit(message, "**Привет!**", markdown=True)

async def register(api):
    api.register_command("hello", hello_command)
```

---

## Частые самые тупые вопросы

<details>
<summary><b>Где взять код подтверждения?</b></summary>

Код придёт в мессенджер Max на ваш телефон после ввода номера.

</details>

<details>
<summary><b>Бот не запускается, что делать?</b></summary>

1. Убедитесь, что Python версии 3.12 или выше: `python --version`
2. Проверьте, что виртуальное окружение активировано (в начале строки должно быть `(venv)`)
3. Попробуйте переустановить зависимости: `pip install -r requirements.txt --force-reinstall`

</details>

<details>
<summary><b>Как обновить бота?</b></summary>

```bash
cd Maximus
git pull
pip install -r requirements.txt --upgrade
```

</details>

<details>
<summary><b>Как удалить сессию и войти заново?</b></summary>

Удалите папку `pymax_session/` в папке проекта и перезапустите бота.

</details>

---

## Лицензия

Этот проект распространяется под лицензией **Apache License 2.0**. 

Подробнее см. в файле [LICENSE](LICENSE).

---

<p align="center">
  <b>⭐ Если вам нравится проект, поставьте звезду на Github! ⭐</b>
</p>

- Проект является улучшенным форком [Maxli](https://github.com/Igroshka/Maxli/tree/main)
