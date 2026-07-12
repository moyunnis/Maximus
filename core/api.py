import asyncio
import json
from pathlib import Path
import traceback
import aiohttp
import aiofiles
import time

# --- КОНФИГУРАЦИЯ ---
BOT_NAME = "Maximus"
BOT_VERSION = "1.0.3"
BOT_VERSION_CODE = 111
MODULES_DIR = Path("modules")
LOG_BUFFER = []

START_TIME = time.time()

def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if minutes:
        parts.append(f"{minutes}м")
    parts.append(f"{secs}с")
    return " ".join(parts)

def _append_log(text: str):
    import logging
    try:
        lines = text.splitlines()
        LOG_BUFFER.extend(lines)
        logger = logging.getLogger("maximus.LOG_BUFFER")
        for line in lines:
            logger.info(line)
        if len(LOG_BUFFER) > 5000:
            del LOG_BUFFER[: len(LOG_BUFFER) - 5000]
    except Exception:
        pass

async def log_critical_error(e, message, client, chat_id=None):
    header = f"\n{'='*50}\n!!! КРИТИЧЕСКАЯ ОШИБКА !!!\nКоманда: {getattr(message, 'text', '')}\nОшибка: {e.__class__.__name__}: {e}\n"
    print(header)
    _append_log(header)
    try:
        tb = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        _append_log(tb)
    except Exception:
        pass

    if not chat_id:
        temp_api = API(client, {})
        temp_api.set_me(client.me)
        chat_id = await temp_api.await_chat_id(message)

    if chat_id:
        try:
            target_chat = next((c for c in client.chats if c.id == chat_id), None)
            if target_chat:
                print("--- JSON ЧАТА ---")
                print(json.dumps(target_chat.__dict__, indent=2, default=str))
        except Exception as err:
            print(f"Ошибка сбора инфо о чате: {err}")
    print("="*50 + "\n")


# --- API ---
class API:
    def __init__(self, client_instance, config_instance):
        self.client = client_instance
        self.config = config_instance
        self.me = None
        self.last_known_chat_id = None
        self.message_to_chat_cache = {}
        self.BOT_NAME = BOT_NAME
        self.BOT_VERSION = BOT_VERSION
        self.BOT_VERSION_CODE = BOT_VERSION_CODE
        self.LOG_BUFFER = LOG_BUFFER
        self.START_TIME = START_TIME

    def get_uptime(self) -> str:
        return format_uptime(time.time() - self.START_TIME)

    def set_me(self, me_instance):
        self.me = me_instance

    def update_last_known_chat_id(self, message):
        """Обновляет память о последнем активном чате."""
        if hasattr(self, 'me') and self.me and message.sender != self.me.contact.id:
            if hasattr(message, 'chat_id') and message.chat_id:
                self.last_known_chat_id = message.chat_id

    async def await_chat_id(self, message):
        """Ищет chat_id по ID сообщения."""
        try:
            message_id_int = int(message.id)
        except (ValueError, TypeError):
            return None

        # Кэш
        if message_id_int in self.message_to_chat_cache:
            return self.message_to_chat_cache[message_id_int]

        # Поиск в чатах по ID последнего сообщения
        for chat in self.client.chats:
            if chat.last_message and chat.last_message.id == message_id_int:
                self.message_to_chat_cache[message_id_int] = chat.id
                return chat.id

        # Избранное (chat_id=0)
        if (hasattr(self, 'me') and self.me and 
            message.sender == self.me.contact.id and 
            hasattr(message, 'chat_id') and message.chat_id == 0):
            self.message_to_chat_cache[message_id_int] = 0
            return 0

        return None

    def clear_message_cache(self, max_size=1000):
        if len(self.message_to_chat_cache) > max_size:
            items = list(self.message_to_chat_cache.items())
            self.message_to_chat_cache = dict(items[-500:])

    async def get_chat_id_for_message(self, message):
        if hasattr(message, 'chat_id') and message.chat_id:
            return message.chat_id
        return await self.await_chat_id(message)

    # --- Отправка и редактирование ---

    async def edit(self, message, text, markdown=False, attaches=None, **kwargs):
        """Редактирует сообщение. Если markdown=True — применяет форматирование."""
        chat_id = getattr(message, 'chat_id', None)
        if chat_id is None:
            chat_id = await self.await_chat_id(message)
        if chat_id is None:
            await log_critical_error(Exception("await_chat_id timeout"), message, self.client)
            return

        notify = kwargs.pop("notify", False)

        try:
            if markdown:
                from pymax.formatting.markdown import Formatter
                clean_text, _ = Formatter.format_markdown(text)
                clean_text = clean_text.rstrip('\n')
                result = await self.client.edit_message(
                    chat_id=chat_id, message_id=int(message.id), text=clean_text
                )
                if result is None:
                    return await self.client.send_message(
                        chat_id=chat_id, text=clean_text, notify=notify
                    )
                return result
            else:
                try:
                    return await self.client.edit_message(
                        chat_id=chat_id, message_id=message.id, text=text, **kwargs
                    )
                except Exception:
                    return await self.client.send_message(
                        chat_id=chat_id, text=text, notify=notify
                    )
        except Exception as e:
            await log_critical_error(e, message, self.client, chat_id)
            try:
                if markdown:
                    from pymax.formatting.markdown import Formatter
                    clean_text, _ = Formatter.format_markdown(text)
                    return await self.client.send_message(
                        chat_id=chat_id, text=clean_text.rstrip('\n'), notify=notify
                    )
                return await self.client.send_message(chat_id=chat_id, text=text, notify=notify)
            except Exception:
                return None

    async def send(self, chat_id, text, markdown=False, attaches=None, **kwargs):
        """Отправляет сообщение в чат."""
        if chat_id is None:
            return None
        notify = kwargs.pop("notify", False)

        if markdown:
            from pymax.formatting.markdown import Formatter
            clean_text, _ = Formatter.format_markdown(text)
            return await self.client.send_message(
                chat_id=chat_id, text=clean_text.rstrip('\n'), notify=notify, **kwargs
            )
        return await self.client.send_message(
            chat_id=chat_id, text=text, notify=notify, **kwargs
        )

    async def send_file(self, chat_id, file_path, text="", markdown=False, **kwargs):
        try:
            from pymax.files import File
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Файл {file_path} не найден")

            file_obj = File(path=str(file_path))
            result = await self.client.send_message(
                chat_id=chat_id, text=text, attachments=[file_obj],
                notify=kwargs.get('notify', True)
            )
            return result
        except Exception as e:
            _append_log(f"❌ Ошибка отправки файла: {e}")
            return None

    async def send_photo(self, chat_id, file_path, text="", markdown=False, **kwargs):
        """Отправляет фотографию в чат. Поддерживает URL и локальные файлы."""
        try:
            from pymax.files import Photo
            import tempfile
            import os

            is_url = isinstance(file_path, str) and (
                file_path.startswith('http://') or file_path.startswith('https://')
            )
            temp_file = None

            if is_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_path) as resp:
                        if resp.status != 200:
                            raise FileNotFoundError(f"Не удалось скачать: {file_path}")
                        suffix = os.path.splitext(file_path)[-1] or '.jpg'
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            temp_file = tmp.name
                            tmp.write(await resp.read())
                file_path = Path(temp_file)
            else:
                file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Файл {file_path} не найден")

            photo = Photo(path=str(file_path))
            result = await self.client.send_message(
                chat_id=chat_id, text=text, attachments=[photo],
                notify=kwargs.get('notify', True)
            )

            if temp_file:
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return result
        except Exception as e:
            print(f"❌ Ошибка отправки фото: {e}")
            return None

    # --- Прочие методы ---

    async def reply(self, message, text, **kwargs):
        """Отвечает в последний известный чат."""
        if self.last_known_chat_id:
            await self.send(self.last_known_chat_id, text, **kwargs)

    async def delete(self, message, for_me=False, **kwargs):
        """Удаляет сообщение."""
        chat_id = getattr(message, 'chat_id', None)
        if not chat_id:
            chat_id = await self.await_chat_id(message)
        if not chat_id:
            return
        try:
            return await self.client.delete_message(
                chat_id=chat_id, message_ids=[message.id], for_me=for_me, **kwargs
            )
        except Exception as e:
            await log_critical_error(e, message, self.client, chat_id)

    async def get_file_url(self, file_id, token, message_id=None, chat_id=None):
        """Возвращает URL файла."""
        return f"https://files.oneme.ru/{file_id}/{token}"

    async def load_from_file(self, message):
        """Загружает модуль из прикреплённого файла."""
        chat_id = getattr(message, 'chat_id', None)
        if not chat_id:
            chat_id = await self.await_chat_id(message)
        if not chat_id:
            return

        await self.client.edit_message(
            chat_id=chat_id, message_id=message.id, text="⏳ Обнаружен файл модуля..."
        )
        attach = message.attaches[0]
        try:
            file_url = getattr(attach, 'url', None)
            file_name = getattr(attach, 'name', "module.py")
            if not file_url:
                await self.client.edit_message(
                    chat_id=chat_id, message_id=message.id, text="❌ Не удалось получить URL."
                )
                return
            if not file_name.endswith(".py"):
                await self.client.edit_message(
                    chat_id=chat_id, message_id=message.id, text="❌ Файл должен быть .py"
                )
                return

            async with aiohttp.ClientSession() as session, session.get(file_url) as resp:
                if resp.status == 200:
                    from .loader import load_module
                    module_path = MODULES_DIR / file_name
                    async with aiofiles.open(module_path, mode='wb') as f:
                        await f.write(await resp.read())
                    response = await load_module(module_path, self)
                    await self.client.edit_message(
                        chat_id=chat_id, message_id=message.id, text=f"Вывод:\n{response}"
                    )
                else:
                    await self.client.edit_message(
                        chat_id=chat_id, message_id=message.id,
                        text=f"❌ Ошибка скачивания: {resp.status}"
                    )
        except Exception as e:
            await log_critical_error(e, message, self.client, chat_id)

    async def get_user_name(self, user_id):
        """Получает имя пользователя по ID."""
        try:
            if not user_id:
                return "Неизвестный"
            user = await self.client.get_user(user_id)
            if user and hasattr(user, 'names') and user.names:
                return user.names[0].name
            return f"Пользователь {user_id}"
        except Exception:
            return f"Пользователь {user_id}"

    async def get_user_info(self, user_id):
        """Получает полную информацию о пользователе."""
        try:
            if not user_id:
                return None
            return await self.client.get_user(user_id)
        except Exception:
            return None

    def get_reply(self, message):
        """Вложенное сообщение-ответ (dict) или None.

        pymax кладёт reply в сырое поле link (type=REPLY), где link['message']
        — процитированное сообщение с полями id, sender, text, attaches.
        """
        link = getattr(message, 'link', None)
        if link is None and getattr(message, 'model_extra', None):
            link = message.model_extra.get('link')
        if not link:
            return None
        if not isinstance(link, dict):
            link = getattr(link, '__dict__', {}) or {}
        replied = link.get('message')
        return replied if isinstance(replied, dict) else None

    def get_reply_id(self, message):
        """ID сообщения, на которое отвечает reply, или None."""
        replied = self.get_reply(message)
        if not replied:
            return None
        rid = replied.get('id')
        try:
            return int(rid)
        except (ValueError, TypeError):
            return rid

    def get_reply_sender(self, message):
        """ID автора сообщения, на которое отвечает reply, или None."""
        replied = self.get_reply(message)
        return replied.get('sender') if replied else None

    def get_sender_name(self, message):
        """Получает имя отправителя сообщения."""
        sender_id = getattr(message, 'sender', None)
        if not sender_id:
            return "Неизвестный"
        try:
            user = self.client.get_cached_user(sender_id)
            if user and hasattr(user, 'names') and user.names:
                return user.names[0].name
        except Exception:
            pass
        return f"Пользователь {sender_id}"

    async def set_reaction(self, message, reaction_id, reaction_type="EMOJI"):
        """Устанавливает реакцию на сообщение."""
        chat_id = getattr(message, 'chat_id', None)
        if not chat_id:
            chat_id = await self.await_chat_id(message)
        if not chat_id:
            return False
        try:
            return await self.client.set_reaction(
                chat_id=chat_id,
                message_id=str(message.id),
                reaction_id=reaction_id,
                reaction_type=reaction_type
            )
        except Exception as e:
            print(f"❌ Ошибка реакции: {e}")
            return False