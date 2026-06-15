# ЛОХАНУЛСЯ! ЭТО НЕ ПОРТАЛ В РОБЛОКС! ТЕПЕРЬ ТЫ РАЗРАБОТЧИК ПЛАГИНОВ ДЛЯ МОЕГО ЮЗЕРБОТА!

# Документация по созданию модулей для Maximus UserBot

> **Maximus** использует библиотеку [PyMax (maxapi-python)](https://github.com/MaxApiTeam/PyMax) — Python-обёртку для MAX Messenger API.

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Структура модуля](#структура-модуля)
3. [Maximus API](#maximus-api)
4. [Прямой доступ к PyMax](#прямой-доступ-к-pymax)
5. [Форматирование текста](#форматирование-текста)
6. [Работа с файлами и медиа](#работа-с-файлами-и-медиа)
7. [Конфигурация модулей](#конфигурация-модулей)
8. [Продвинутые возможности](#продвинутые-возможности)
9. [Примеры модулей](#примеры-модулей)

---

## Быстрый старт

### Минимальный модуль

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

### Загрузка модуля

1. Создайте файл `.py` с кодом модуля
2. Отправьте файл боту с командой `.load`
3. Или положите файл в папку `modules/` и перезапустите бота
4. Используйте команду с префиксом (например `.hello`)

---

## Структура модуля

### Обязательные метаданные

```python
# name: Название модуля
# version: 1.0.0
# developer: Имя разработчика
# id: unique_module_id
# min-Maximus: 100
```

| Поле | Описание |
|------|----------|
| `name` | Отображаемое название модуля |
| `version` | Версия модуля (semver) |
| `developer` | Имя разработчика |
| `id` | Уникальный ID (2-32 символа, латиница, цифры, `-`, `_`) |
| `min-Maximus` | **Минимальный код версии Maximus** для работы модуля (текущий: `100`) |

> **Важно:** Ключ `min-Maximus` пишется **именно так**, с большой буквы `M`. Loader ищет точное совпадение.

### Основные функции

```python
async def register(api):
    """Вызывается при загрузке модуля."""
    api.register_command("cmd", command_handler)
    api.register_watcher(watcher_handler)

async def command_handler(api, message, args):
    """Обработчик команды.
    
    Args:
        api: Объект Maximus API
        message: Объект сообщения (pymax.Message)
        args: Список аргументов команды
    """
    pass

async def watcher_handler(api, message):
    """Вотчер — обрабатывает все входящие сообщения."""
    pass
```

---

## Maximus API

Maximus предоставляет удобную обёртку над PyMax с дополнительными функциями.

### Работа с сообщениями

```python
# Редактирование сообщения (с поддержкой markdown)
await api.edit(message, "**Жирный** и *курсив*", markdown=True)

# Отправка нового сообщения
chat_id = await api.get_chat_id_for_message(message)
await api.send(chat_id, "Привет!", markdown=True)

# Ответ в последний известный чат
await api.reply(message, "Ответ", markdown=True)

# Удаление сообщения
await api.delete(message)
await api.delete(message, for_me=True)  # Только у себя
```

### Получение chat_id

```python
# Способ 1: Из атрибута сообщения (если доступен)
chat_id = getattr(message, 'chat_id', None)

# Способ 2: Через API (с кэшем и fallback)
chat_id = await api.get_chat_id_for_message(message)

# Способ 3: Полный поиск
chat_id = await api.await_chat_id(message)
```

### Реакции

```python
await api.set_reaction(message, "❤️")
await api.set_reaction(message, "👍", reaction_type="EMOJI")
```

### Информация о пользователях

```python
# Имя пользователя по ID
name = await api.get_user_name(user_id)

# Полная информация о пользователе
user = await api.get_user_info(user_id)

# Имя отправителя (синхронно, из кэша)
sender_name = api.get_sender_name(message)
```

### Свойства API

```python
api.BOT_NAME          # "Maximus"
api.BOT_VERSION       # "1.0.0"
api.BOT_VERSION_CODE  # 100
api.me                # Профиль текущего пользователя (Profile)
api.me.contact        # Данные пользователя (User)
api.me.contact.id     # ID текущего пользователя
api.client            # Прямой доступ к PyMax клиенту
api.config            # Конфигурация бота
api.LOG_BUFFER        # Буфер логов
```

---

## Прямой доступ к PyMax

Вы можете использовать все возможности PyMax напрямую через `api.client`.

### Основные методы

```python
client = api.client

# Отправка сообщений
await client.send_message(chat_id=123, text="Привет!")
await client.send_message(chat_id=123, text="С фото", attachments=[photo])

# Редактирование
await client.edit_message(chat_id=123, message_id=456, text="Новый текст")

# Удаление
await client.delete_message(chat_id=123, message_ids=[456, 789])

# Пользователи
user = await client.get_user(user_id)

# Чаты (в новой версии PyMax нет dialogs — только chats)
chat = await client.get_chat(chat_id)
chats = await client.fetch_chats()  # Пагинация
chats = await client.get_chats([id1, id2])  # По списку ID
```

### Доступные модели

```python
from pymax import (
    Message,   # Сообщение
    User,      # Пользователь
    Chat,      # Чат
    Profile,   # Профиль (обёртка над User, лежит в client.me)
    Photo,     # Фото
    File,      # Файл
    Video,     # Видео
)
```

### Обработчики событий

PyMax поддерживает декораторы для регистрации обработчиков:

```python
client = api.client

@client.on_message()
async def handle_message(message: Message, client: Client):
    print(f"Новое сообщение: {message.text}")

@client.on_message_edit()
async def handle_edit(message: Message, client: Client):
    print(f"Отредактировано: {message.text}")

@client.on_message_delete()
async def handle_delete(event, client: Client):
    print(f"Удалено: {event}")

@client.on_reaction_update()
async def handle_reaction(event, client: Client):
    print(f"Реакция: {event}")
```

---

## Форматирование текста

### Markdown синтаксис

При `markdown=True` поддерживается:

| Синтаксис | Результат | Тип |
|-----------|-----------|-----|
| `**текст**` | **жирный** | STRONG |
| `*текст*` | *курсив* | EMPHASIZED |
| `__текст__` | <u>подчёркнутый</u> | UNDERLINE |
| `~~текст~~` | ~~зачёркнутый~~ | STRIKETHROUGH |

### Пример

```python
await api.edit(message, """
**Жирный текст**
*Курсивный текст*
__Подчёркнутый текст__
~~Зачёркнутый текст~~
""", markdown=True)
```

### Программное создание форматирования

```python
from pymax.formatting.markdown import Formatter

# Парсинг markdown
clean_text, elements = Formatter.format_markdown("**bold** *italic*")
# clean_text: "bold italic"
# elements: [Element(type='STRONG', from_=0, length=4), ...]
```

---

## Работа с файлами и медиа

### Отправка файлов

```python
chat_id = await api.get_chat_id_for_message(message)

# Локальный файл
await api.send_file(chat_id, "path/to/file.txt", text="Описание")

# Фото (локальное или URL)
await api.send_photo(chat_id, "path/to/image.jpg", text="**Красиво!**", markdown=True)
await api.send_photo(chat_id, "https://example.com/img.jpg", text="Из интернета")
```

### Получение файлов из сообщений

```python
if message.attaches:
    for attach in message.attaches:
        file_name = getattr(attach, 'name', 'unknown')
        file_url = getattr(attach, 'url', None)
        print(f"Файл: {file_name}, URL: {file_url}")
```

### Получение URL файла

```python
file_url = await api.get_file_url(
    file_id=attach.file_id,
    token=attach.token,
    message_id=message.id,
    chat_id=chat_id
)
```

---

## Конфигурация модулей

```python
from core.config import register_module_settings, get_module_setting, set_module_setting

async def register(api):
    register_module_settings("my_module", {
        "enabled": {"default": True, "description": "Включить модуль"},
        "prefix": {"default": "!", "description": "Префикс команд"},
    })

# Использование
enabled = get_module_setting("my_module", "enabled", True)
set_module_setting("my_module", "enabled", False)
```

---

## Продвинутые возможности

### Вотчеры

```python
async def auto_reply_watcher(api, message):
    """Автоматический ответ на приветствие."""
    if message.sender == api.me.contact.id:
        return
    text = getattr(message, 'text', '').lower()
    if text in ["привет", "hi", "hello"]:
        await api.reply(message, "Привет!", markdown=True)

async def register(api):
    api.register_watcher(auto_reply_watcher)
```

### Обработка ошибок

```python
async def safe_command(api, message, args):
    try:
        result = await some_operation()
        await api.edit(message, f"**Готово:** {result}", markdown=True)
    except Exception as e:
        await api.edit(message, f"**Ошибка:** {e}", markdown=True)
        api.LOG_BUFFER.append(f"[{__name__}] Error: {e}")
```

### Асинхронные операции

```python
import asyncio

async def parallel_command(api, message, args):
    await api.edit(message, "Исполняю...", markdown=True)
    results = await asyncio.gather(task1(), task2(), task3(), return_exceptions=True)
    await api.edit(message, f"Готово: {results}", markdown=True)
```

---

## Примеры модулей

### Модуль с настройками

```python
# name: Приветствие
# version: 1.0.0
# developer: Example
# id: greeter
# min-Maximus: 100

from core.config import register_module_settings, get_module_setting, set_module_setting

async def greet_command(api, message, args):
    """Приветствует с настраиваемым текстом."""
    text = get_module_setting("greeter", "message", "Привет!")
    await api.edit(message, text, markdown=True)

async def set_greeting_command(api, message, args):
    """Устанавливает текст приветствия."""
    if not args:
        await api.edit(message, "Укажите текст", markdown=True)
        return
    new_text = " ".join(args)
    set_module_setting("greeter", "message", new_text)
    await api.edit(message, f"Установлено: **{new_text}**", markdown=True)

async def register(api):
    register_module_settings("greeter", {
        "message": {"default": "Привет!", "description": "Текст приветствия"}
    })
    api.register_command("greet", greet_command)
    api.register_command("setgreet", set_greeting_command)
```

### Модуль загрузки файлов

```python
# name: Файловый менеджер
# version: 1.0.0
# developer: Example
# id: file_manager
# min-Maximus: 100

import os

async def upload_command(api, message, args):
    """Загружает файл в чат."""
    if not args:
        await api.edit(message, "Укажите путь к файлу", markdown=True)
        return
    
    file_path = " ".join(args)
    if not os.path.exists(file_path):
        await api.edit(message, f"Файл не найден: **{file_path}**", markdown=True)
        return
    
    chat_id = await api.get_chat_id_for_message(message)
    await api.edit(message, "Загружаю файл...", markdown=True)
    await api.send_file(chat_id, file_path, text=f"**{os.path.basename(file_path)}**", markdown=True)
    await api.delete(message)

async def register(api):
    api.register_command("upload", upload_command)
```

---

## Обязательные к исполнению ~~приказы~~ советы

1. Всегда используйте `markdown=True` для форматированного текста
2. Оборачивайте код в `try/except`
3. Используйте docstring для документирования команд (они попадают в `.help`)
4. Проверяйте `min-Maximus` для совместимости
5. Используйте `api.client` для прямого доступа к PyMax
6. Логируйте ошибки в `api.LOG_BUFFER`
7. Помните: `api.me.contact.id` — это ID текущего пользователя (не `api.me.id`)

## Неплохо для изучения ссылки

- **PyMax на GitHub:** https://github.com/MaxApiTeam/PyMax
- **PyMax на PyPI:** `pip install maxapi-python`
- **Maximus:** [https://codeberg.org/moyunni/Maximus]