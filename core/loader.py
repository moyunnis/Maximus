import importlib.util
import sys
import subprocess
import re
from pathlib import Path
from core.api import BOT_VERSION_CODE, MODULES_DIR

COMMANDS = {}
MODULE_COMMANDS = {}
LOADED_MODULES = {}
WATCHERS = [] # Новый список для вотчеров
MODULE_IDS = {} # Словарь для отслеживания ID модулей: {module_id: module_name}
 
class ModuleAPIWrapper:
    def __init__(self, module_name, api):
        self._module_name = module_name
        self._api = api
        
        # Делаем все методы API доступными напрямую
        for attr_name in dir(api):
            if not attr_name.startswith('_') and callable(getattr(api, attr_name)):
                setattr(self, attr_name, getattr(api, attr_name))

    def register_command(self, command_name, function):
        if command_name in COMMANDS:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Модуль '{self._module_name}' попытался перезаписать системную команду '{command_name}'. Отказано.")
            return False
        description = function.__doc__ or "Без описания."
        MODULE_COMMANDS[command_name] = {'function': function, 'description': description}
        if self._module_name not in LOADED_MODULES: LOADED_MODULES[self._module_name] = {'commands': {}, 'watchers': []}
        LOADED_MODULES[self._module_name]['commands'][command_name] = description
        return True
    
    def register_watcher(self, function):
        """Регистрирует функцию, которая будет вызываться на каждое сообщение."""
        WATCHERS.append(function)
        if self._module_name not in LOADED_MODULES: LOADED_MODULES[self._module_name] = {'commands': {}, 'watchers': []}
        LOADED_MODULES[self._module_name]['watchers'].append(function)
        print(f"Модуль '{self._module_name}' зарегистрировал вотчер.")
    
    # Дополнительные удобные методы для модулей
    async def send_message(self, chat_id, text, **kwargs):
        """Отправляет сообщение в чат."""
        return await self._api.send(chat_id, text, **kwargs)
    
    async def edit_message(self, message, text, **kwargs):
        """Редактирует сообщение."""
        return await self._api.edit(message, text, **kwargs)
    
    async def delete_message(self, message, **kwargs):
        """Удаляет сообщение."""
        return await self._api.delete(message, **kwargs)
    
    async def reply_to_message(self, message, text, **kwargs):
        """Отвечает на сообщение."""
        return await self._api.reply(message, text, **kwargs)
    
    async def send_photo(self, chat_id, file_path, text="", **kwargs):
        """Отправляет фотографию в чат."""
        return await self._api.send_photo(chat_id, file_path, text, **kwargs)
    
    async def send_file(self, chat_id, file_path, text="", **kwargs):
        """Отправляет файл в чат."""
        return await self._api.send_file(chat_id, file_path, text, **kwargs)
    
    def get_chat_id(self, message):
        """Получает chat_id из сообщения."""
        return getattr(message, 'chat_id', None)
    
    def get_sender_id(self, message):
        """Получает ID отправителя сообщения."""
        return getattr(message, 'sender', None)
    
    def get_message_text(self, message):
        """Получает текст сообщения."""
        return getattr(message, 'text', '')
    
    def get_message_id(self, message):
        """Получает ID сообщения."""
        return getattr(message, 'id', None)

def version_to_tuple(v: str):
    try: return tuple(map(int, v.split('.')))
    except: return (0,0,0)

def validate_module_id(module_id: str) -> tuple[bool, str]:
    """
    Валидирует ID модуля согласно требованиям:
    - 2-32 символа
    - Начинается с буквы
    - Содержит только латинские буквы, цифры, дефисы и подчеркивания
    
    Returns:
        (is_valid, error_message)
    """
    if not module_id:
        return False, "ID модуля не может быть пустым"
    
    if len(module_id) < 2 or len(module_id) > 32:
        return False, "ID модуля должен быть от 2 до 32 символов"
    
    if not module_id[0].isalpha():
        return False, "ID модуля должен начинаться с буквы"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', module_id):
        return False, "ID модуля может содержать только латинские буквы, цифры, дефисы и подчеркивания"
    
    return True, ""

def check_duplicate_module_id(module_id: str, module_name: str) -> tuple[bool, str]:
    """
    Проверяет, не используется ли уже этот ID модуля.
    
    Returns:
        (is_duplicate, error_message)
    """
    if module_id in MODULE_IDS and MODULE_IDS[module_id] != module_name:
        return True, f"ID '{module_id}' уже используется модулем '{MODULE_IDS[module_id]}'"
    
    return False, ""

def parse_module_header(path: Path):
    header = { 
        "name": None, 
        "version": None, 
        "developer": None, 
        "dependencies": [], 
        "min-Maximus": None, 
        "id": None,
        "description": None
    }
    with open(path, 'r', encoding='utf-8') as f:
        for line in f.readlines()[:15]:  # Увеличиваем количество строк для поиска
            if line.startswith('#'):
                for key in ["name", "version", "developer", "dependencies", "min-Maximus", "id", "description"]:
                    match = re.search(rf"^\s*#\s*{key}\s*:\s*(.+)", line)
                    if match:
                        value = match.group(1).strip()
                        if key == "dependencies": 
                            header[key] = [d.strip() for d in value.split(',') if d.strip()]
                        else: 
                            header[key] = value
    
    # Если ID не указан, используем имя файла как ID
    if not header["id"]:
        header["id"] = path.stem
    
    return header

async def load_module(module_path: Path, api):
    module_name = module_path.stem
    
    # Проверяем, загружен ли модуль с таким же ID
    header = parse_module_header(module_path)
    module_id = header.get('id', module_name)
    
    # Если модуль с таким ID уже загружен, выгружаем его
    existing_module = None
    for name, data in LOADED_MODULES.items():
        if data.get('header', {}).get('id') == module_id:
            existing_module = name
            break
    
    if existing_module:
        # При перезагрузке не удаляем файл модуля с диска
        unload_result = await unload_module(existing_module, remove_file=False)
        print(f"🔁 Заменяем модуль '{existing_module}' на '{module_name}': {unload_result}")
    
        
    # Сохраняем состояние до загрузки для возможного отката
    was_module_loaded = module_name in LOADED_MODULES
    original_commands = {}
    original_watchers = []
    
    # Валидация обязательных полей
    required_fields = ["name", "version", "developer", "min-Maximus", "id"]
    missing_fields = [field for field in required_fields if not header.get(field)]
    
    if missing_fields:
        return f"❌ Отсутствуют обязательные поля в метаданных модуля: {', '.join(missing_fields)}. Модуль не может быть загружен."
    
    # Валидация ID модуля
    module_id = header["id"]
    is_valid, error_msg = validate_module_id(module_id)
    if not is_valid:
        return f"❌ Ошибка валидации ID модуля: {error_msg}"
    
        # Проверка на дублирование ID больше не нужна, так как мы заменяем модули с одинаковым ID
    
    # Переименование файла модуля по ID, если ID отличается от имени файла
    if module_id != module_name:
        new_module_path = module_path.parent / f"{module_id}.py"
        
        # Если файл с ID уже существует и это не тот же файл, удаляем старый
        if new_module_path.exists() and new_module_path != module_path:
            try:
                new_module_path.unlink()
                print(f"🗑️ Удален старый файл модуля: {new_module_path.name}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить старый файл: {e}")
        
        try:
            # Переименовываем файл
            module_path.rename(new_module_path)
            module_path = new_module_path
            module_name = module_id
            print(f"📝 Модуль переименован: {module_path.stem}.py → {module_id}.py")
        except Exception as e:
            return f"❌ Ошибка переименования модуля: {e}"
    
    required_version = int(header["min-Maximus"])
    current_version = BOT_VERSION_CODE
    if current_version < required_version: return f"❌ Ошибка: модуль '{header['name']}' требует Maximus v{header['min-Maximus']}. Ваша версия: v{BOT_VERSION_CODE}."
    
    # Устанавливаем зависимости с возможностью отката
    installed_dependencies = []
    if header["dependencies"]:
        try:
            print(f"  Установка зависимостей для {module_name}: {header['dependencies']}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *header['dependencies']])
            installed_dependencies = header['dependencies'].copy()
        except subprocess.CalledProcessError as e: 
            return f"❌ Ошибка установки зависимостей: {e}"
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec); sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, "register"):
            # Сохраняем состояние команд и вотчеров для отката
            if module_name in LOADED_MODULES:
                original_commands = LOADED_MODULES[module_name].get('commands', {}).copy()
                original_watchers = LOADED_MODULES[module_name].get('watchers', []).copy()
            
            LOADED_MODULES[module_name] = {'header': header, 'commands': {}, 'watchers': []}
            
            try:
                await module.register(ModuleAPIWrapper(module_name, api))
                
                # Регистрируем ID модуля
                MODULE_IDS[module_id] = module_name
                
                version = header.get('version', '1.0.0')
                return f"✅ Модуль '{header.get('name', module_name)}' (ID: {module_id}) v{version} успешно загружен."
            except Exception as register_error:
                # Откат при ошибке регистрации
                print(f"❌ Ошибка при регистрации модуля '{module_name}': {register_error}")
                await rollback_module(module_name, was_module_loaded, original_commands, original_watchers)
                return f"❌ Ошибка регистрации модуля '{module_name}': {register_error}"
        else:
            if module_name in sys.modules: del sys.modules[module_name]
            return f"❌ Ошибка: в модуле '{module_name}' нет функции register()."
    except Exception as e:
                # Откат при критической ошибке
        print(f"❌ Критическая ошибка при загрузке '{module_name}': {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        await rollback_module(module_name, was_module_loaded, original_commands, original_watchers)
        
        # Удаляем файл сломанного модуля
        if module_path.exists():
            try:
                module_path.unlink()
                print(f"🧹 Удален файл сломанного модуля: {module_path}")
            except Exception as delete_error:
                print(f"⚠️ Не удалось удалить файл модуля: {delete_error}")
        
        return f"❌ Критическая ошибка при загрузке '{module_name}': {e}. Файл модуля удален."

async def rollback_module(module_name, was_loaded, original_commands, original_watchers):
    """Откатывает изменения модуля при ошибке загрузки."""
    try:
        # Восстанавливаем команды
        if module_name in LOADED_MODULES:
            current_commands = LOADED_MODULES[module_name].get('commands', {})
            for cmd in current_commands:
                if cmd in MODULE_COMMANDS:
                    del MODULE_COMMANDS[cmd]
            
            # Восстанавливаем оригинальные команды
            for cmd, desc in original_commands.items():
                if cmd in MODULE_COMMANDS:
                    MODULE_COMMANDS[cmd] = {'function': None, 'description': desc}
        
        # Восстанавливаем вотчеры
        if module_name in LOADED_MODULES:
            current_watchers = LOADED_MODULES[module_name].get('watchers', [])
            for watcher in current_watchers:
                if watcher in WATCHERS:
                    WATCHERS.remove(watcher)
            
            # Восстанавливаем оригинальные вотчеры
            for watcher in original_watchers:
                if watcher not in WATCHERS:
                    WATCHERS.append(watcher)
        
        # Если модуль не был загружен ранее, удаляем его из LOADED_MODULES
        if not was_loaded and module_name in LOADED_MODULES:
            del LOADED_MODULES[module_name]
        
        # Удаляем модуль из sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        print(f"🔄 Откат модуля '{module_name}' выполнен")
        
    except Exception as rollback_error:
        print(f"❌ Ошибка при откате модуля '{module_name}': {rollback_error}")

async def unload_module(module_name: str, remove_file: bool = True):
    if module_name not in LOADED_MODULES: return f"Модуль '{module_name}' не загружен."
    
    # Получаем ID модуля для удаления из словаря
    module_header = LOADED_MODULES[module_name].get('header', {})
    module_id = module_header.get('id', module_name)
    
    # Выгружаем команды
    commands_to_remove = list(LOADED_MODULES[module_name].get('commands', {}).keys())
    for cmd in commands_to_remove:
        if cmd in MODULE_COMMANDS: del MODULE_COMMANDS[cmd]
    # Выгружаем вотчеры
    watchers_to_remove = LOADED_MODULES[module_name].get('watchers', [])
    for watcher in watchers_to_remove:
        if watcher in WATCHERS: WATCHERS.remove(watcher)
    
    # Удаляем ID из словаря
    if module_id in MODULE_IDS:
        del MODULE_IDS[module_id]
    
    # Удаляем конфиг модуля
    from core.config import config, save_config
    if module_id in config:
        del config[module_id]
        print(f"🧹 Удален конфиг модуля '{module_id}'")
    if module_name in config and module_name != module_id:
        del config[module_name]
        print(f"🧹 Удален конфиг модуля '{module_name}'")
    save_config(config)
        
    del LOADED_MODULES[module_name]
    if module_name in sys.modules: del sys.modules[module_name]
    if remove_file:
        (MODULES_DIR / f"{module_name}.py").unlink(missing_ok=True)
    return f"✅ Модуль '{module_name}' (ID: {module_id}) успешно выгружен и удален."

async def register_system_module(module):
    if hasattr(module, "register"):
        await module.register(COMMANDS)

async def load_all_modules(api):
    print("--- Загрузка системных модулей ---")
    from core_modules import info, management, ping, settings, modules, restart
    await register_system_module(info); await register_system_module(management)
    await register_system_module(ping); await register_system_module(settings)
    await register_system_module(modules); await register_system_module(restart)
    MODULES_DIR.mkdir(exist_ok=True)
    print("--- Автозагрузка пользовательских модулей ---")
    loaded_files = set()  # Отслеживаем загруженные файлы
    for file in MODULES_DIR.glob("*.py"):
        if file.stem != "__init__":
            # Проверяем, не был ли этот файл уже загружен (переименован)
            if file.name not in loaded_files:
                result = await load_module(file, api)
                print(f"  - {file.name}: {result}")
                # Если файл был переименован, добавляем новое имя в список
                if "переименован" in result or "успешно загружен" in result:
                    # Получаем новое имя файла из результата или из MODULE_IDS
                    for module_id, module_name in MODULE_IDS.items():
                        if module_name == file.stem:
                            loaded_files.add(f"{module_id}.py")
                            break
                loaded_files.add(file.name)
    print("---------------------------------------")
