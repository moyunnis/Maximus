# name: Maximus Store
# version: 2.2.0
# developer: @zoyuki (tg)
# id: maximus_store
# dependencies: aiohttp
# min-Maximus: 100

import aiohttp
import os
import re
import time
from pathlib import Path
from core.api import MODULES_DIR
from core.loader import load_module, LOADED_MODULES, MODULE_IDS

REPO_URL = "https://github.com/zoyuki/MaximusStore"
REPO_OWNER = "zoyuki"
REPO_NAME = "MaximusStore"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main"

PENDING_UPDATES = {}
UPDATES_TTL = 600


def get_prefix(api):
    """Получает текущий префикс из конфига."""
    return api.config.get('prefix', '.')


def version_to_tuple(v: str):
    """Преобразует строку версии в кортеж для сравнения."""
    try:
        clean = re.sub(r'[^0-9.]', '', v)
        return tuple(map(int, clean.split('.')))
    except Exception:
        return (0, 0, 0)


def parse_header_from_text(text: str):
    """Парсит метаданные модуля из текста файла."""
    header = {
        "name": None,
        "version": None,
        "developer": None,
        "id": None,
    }
    for line in text.splitlines()[:15]:
        if not line.startswith('#'):
            continue
        for key in ["name", "version", "developer", "id"]:
            match = re.search(rf"^\s*#\s*{key}\s*:\s*(.+)", line, re.IGNORECASE)
            if match:
                header[key] = match.group(1).strip()
    return header


def get_local_modules_info():
    """Собирает информацию о локально установленных модулях: {id: {name, version, file_path}}."""
    local = {}
    
    for name, data in LOADED_MODULES.items():
        header = data.get('header', {})
        mod_id = header.get('id', name)
        local[mod_id] = {
            'name': header.get('name', name),
            'version': header.get('version', '0.0.0'),
            'file_name': f"{name}.py",
            'file_path': MODULES_DIR / f"{name}.py",
        }
    
    for file_path in MODULES_DIR.glob("*.py"):
        if file_path.stem == "__init__":
            continue
        try:
            text = file_path.read_text(encoding='utf-8')
            header = parse_header_from_text(text)
            mod_id = header.get('id') or file_path.stem
            if mod_id not in local:
                local[mod_id] = {
                    'name': header.get('name', file_path.stem),
                    'version': header.get('version', '0.0.0'),
                    'file_name': file_path.name,
                    'file_path': file_path,
                }
        except Exception:
            continue
    
    return local


async def get_remote_modules_with_versions():
    """Получает модули из репо с их метаданными (скачивает каждый файл)."""
    try:
        api_url = f"{API_BASE}/contents/"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Maximus-Bot/2.2",
                "Accept": "application/json"
            }
            
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                contents = await response.json()
                py_files = [item for item in contents if item['type'] == 'file' and item['name'].endswith('.py')]
                
                remote = {}
                for file_info in py_files:
                    try:
                        raw_url = f"{RAW_BASE}/{file_info['path']}"
                        async with session.get(raw_url, headers=headers) as file_resp:
                            if file_resp.status == 200:
                                text = await file_resp.text()
                                header = parse_header_from_text(text)
                                mod_id = header.get('id') or file_info['name'].replace('.py', '')
                                remote[mod_id] = {
                                    'name': header.get('name', file_info['name'].replace('.py', '')),
                                    'version': header.get('version', '0.0.0'),
                                    'file_name': file_info['name'],
                                    'file_path': file_info['path'],
                                    'size': file_info.get('size', 0),
                                }
                    except Exception:
                        continue
                
                return remote
    except Exception:
        return None


async def su_command(api, message, args):
    """Проверяет доступные обновления модулей."""
    prefix = get_prefix(api)
    await api.edit(message, "🔍 Сверяю версии модулей с репозиторием...")
    
    try:
        local = get_local_modules_info()
        if not local:
            await api.edit(message, "📭 У вас нет установленных модулей.")
            return
        
        remote = await get_remote_modules_with_versions()
        if remote is None:
            await api.edit(message, f"❌ Не удалось подключиться к репозиторию\n📂 {REPO_OWNER}/{REPO_NAME}")
            return
        
        if not remote:
            await api.edit(message, "📭 Репозиторий пуст.")
            return
        
        updates = []
        outdated = []
        
        for mod_id, local_info in local.items():
            if mod_id not in remote:
                continue
            
            remote_info = remote[mod_id]
            local_v = version_to_tuple(local_info['version'])
            remote_v = version_to_tuple(remote_info['version'])
            
            if remote_v > local_v:
                updates.append({
                    'id': mod_id,
                    'name': remote_info['name'],
                    'local_version': local_info['version'],
                    'remote_version': remote_info['version'],
                    'file_name': remote_info['file_name'],
                    'file_path': remote_info['file_path'],
                })
            elif local_v > remote_v:
                outdated.append({
                    'id': mod_id,
                    'name': local_info['name'],
                    'local_version': local_info['version'],
                    'remote_version': remote_info['version'],
                })
        
        response_parts = [f"🔄 **Проверка обновлений**\n📂 {REPO_OWNER}/{REPO_NAME}\n"]
        
        if updates:
            response_parts.append(f"🆕 **Доступно обновлений: {len(updates)}**\n")
            for u in updates:
                response_parts.append(
                    f"• **{u['name']}** `{u['local_version']}` → `{u['remote_version']}`"
                )
            response_parts.append("")
            
            PENDING_UPDATES['modules'] = updates
            PENDING_UPDATES['created_at'] = time.time()
            PENDING_UPDATES['expires_at'] = time.time() + UPDATES_TTL
            
            response_parts.append(f"💡 Для обновления: `{prefix}sg` или `{prefix}sg y`")
        else:
            response_parts.append("✅ Все модули актуальны!")
        
        if outdated:
            response_parts.append(f"\n⚠️ **Старые версии (у вас новее): {len(outdated)}**\n")
            for o in outdated:
                response_parts.append(
                    f"• **{o['name']}** `{o['local_version']}` ≠ `{o['remote_version']}`"
                )
        
        await api.edit(message, "\n".join(response_parts), markdown=True)
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка проверки: {e}")


async def sg_command(api, message, args):
    """Управление обновлениями модулей."""
    prefix = get_prefix(api)
    arg = args[0].lower() if args else None
    
    if arg == 'y':
        if PENDING_UPDATES and PENDING_UPDATES.get('expires_at', 0) > time.time():
            updates = PENDING_UPDATES['modules']
        else:
            await api.edit(message, "🔍 Проверяю доступные обновления...")
            local = get_local_modules_info()
            remote = await get_remote_modules_with_versions()
            
            if remote is None:
                await api.edit(message, f"❌ Не удалось подключиться к репозиторию")
                return
            
            updates = []
            for mod_id, local_info in local.items():
                if mod_id not in remote:
                    continue
                remote_info = remote[mod_id]
                if version_to_tuple(remote_info['version']) > version_to_tuple(local_info['version']):
                    updates.append({
                        'id': mod_id,
                        'name': remote_info['name'],
                        'local_version': local_info['version'],
                        'remote_version': remote_info['version'],
                        'file_name': remote_info['file_name'],
                        'file_path': remote_info['file_path'],
                    })
        
        if not updates:
            await api.edit(message, "✅ Нечего обновлять — все модули актуальны!")
            return
        
        await api.edit(message, f"⬇️ Обновляю {len(updates)} модулей...")
        results = []
        
        for u in updates:
            try:
                raw_url = f"{RAW_BASE}/{u['file_path']}"
                file_content = await download_file(raw_url)
                if not file_content:
                    results.append(f"❌ **{u['name']}** — не удалось скачать")
                    continue
                
                module_path = MODULES_DIR / u['file_name']
                with open(module_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                load_result = await load_module(module_path, api)
                
                if "успешно загружен" in load_result.lower() or "✅" in load_result:
                    results.append(
                        f"✅ **{u['name']}** `{u['local_version']}` → `{u['remote_version']}`"
                    )
                else:
                    results.append(
                        f"⚠️ **{u['name']}** — сохранён, но ошибка загрузки: {load_result}"
                    )
            except Exception as e:
                results.append(f"❌ **{u['name']}** — ошибка: {e}")
        
        PENDING_UPDATES.clear()
        
        response = f"🔄 **Результаты обновления ({len(updates)} модулей):**\n\n" + "\n".join(results)
        await api.edit(message, response, markdown=True)
        return
    
    if arg == 'n':
        if not PENDING_UPDATES or PENDING_UPDATES.get('expires_at', 0) <= time.time():
            await api.edit(message, "ℹ️ Нет ожидающих обновлений для отмены.")
            return
        
        count = len(PENDING_UPDATES.get('modules', []))
        PENDING_UPDATES.clear()
        await api.edit(message, f"❌ Обновление отменено ({count} модулей).")
        return
    
    if not PENDING_UPDATES or PENDING_UPDATES.get('expires_at', 0) <= time.time():
        await api.edit(
            message,
            f"ℹ️ Нет ожидающих обновлений.\n\n"
            f"Сначала выполните `{prefix}su` для проверки обновлений,\n"
            f"или сразу `{prefix}sg y` для обновления без проверки.",
            markdown=True
        )
        return
    
    updates = PENDING_UPDATES['modules']
    expires_in = int(PENDING_UPDATES['expires_at'] - time.time())
    
    response_parts = [f"📦 **Ожидающие обновления ({len(updates)}):**\n"]
    for u in updates:
        response_parts.append(
            f"• **{u['name']}** `{u['local_version']}` → `{u['remote_version']}`"
        )
    
    response_parts.append(f"\n⏳ Действительно {expires_in // 60} мин")
    response_parts.append(f"\n💡 `{prefix}sg y` — применить")
    response_parts.append(f"💡 `{prefix}sg n` — отменить")
    
    await api.edit(message, "\n".join(response_parts), markdown=True)

async def ss_command(api, message, args):
    """Поиск модулей в репозитории (до 20 результатов)."""
    prefix = get_prefix(api)
    
    if not args:
        await api.edit(message, f"❌ Укажите запрос: `{prefix}ss weather`", markdown=True)
        return
    
    search_query = " ".join(args).lower()
    await api.edit(message, f"🔍 Поиск: '{search_query}'...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, f"❌ Не удалось загрузить модули из репозитория\n📂 {REPO_OWNER}/{REPO_NAME}")
            return
        
        matched = [m for m in modules if search_query in m['name'].lower().replace('.py', '')][:20]
        
        if not matched:
            await api.edit(
                message, 
                f"❌ Не найдено по запросу: '{search_query}'\n\n"
                f"💡 `{prefix}sl` — все модули",
                markdown=True
            )
            return
        
        await show_results(api, message, matched, search_query)
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")


async def sl_command(api, message, args):
    """Список всех модулей."""
    prefix = get_prefix(api)
    await api.edit(message, "📋 Загружаю список...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, "❌ Не удалось загрузить модули")
            return
        
        response = [f"📦 Все модули ({len(modules)}):\n"]
        response.append(f"📂 {REPO_OWNER}/{REPO_NAME}")
        response.append(f"🔗 {REPO_URL}\n")
        
        for i, module in enumerate(modules[:30], 1):
            name = module['name'].replace('.py', '')
            size_kb = module.get('size', 0) / 1024
            response.append(f"{i}. {name} ({size_kb:.1f} KB)")
        
        if len(modules) > 30:
            response.append(f"\n... и еще {len(modules) - 30} модулей")
        
        response.append(f"\n💾 `{prefix}sd <номер>` — скачать и установить")
        response.append(f"💾 `{prefix}sd <название>` — скачать по имени")
        response.append(f"🔍 `{prefix}ss <запрос>` — поиск")
        
        await api.edit(message, "\n".join(response), markdown=True)
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")


async def sd_command(api, message, args):
    """Скачать модуль и сразу установить его в modules/."""
    prefix = get_prefix(api)
    
    if not args:
        await api.edit(
            message, 
            f"❌ Укажите номер или название модуля.\n\n"
            f"**Примеры:**\n"
            f"• `{prefix}sd 1` — скачать первый модуль из списка\n"
            f"• `{prefix}sd weather` — скачать модуль по имени",
            markdown=True
        )
        return
    
    await api.edit(message, "🔄 Получаю список модулей...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, "❌ Не удалось загрузить список модулей")
            return
        
        query = args[0]
        module = None
        
        if query.isdigit():
            module_number = int(query)
            if module_number < 1 or module_number > len(modules):
                await api.edit(message, f"❌ Неверный номер. Доступно: 1-{len(modules)}")
                return
            module = modules[module_number - 1]
        else:
            search_query = " ".join(args).lower()
            matched = [m for m in modules if m['name'].lower().replace('.py', '') == search_query]
            if not matched:
                matched = [m for m in modules if search_query in m['name'].lower().replace('.py', '')]
            
            if not matched:
                await api.edit(message, f"❌ Модуль '{query}' не найден в репозитории")
                return
            if len(matched) > 1:
                names = "\n".join([f"• {m['name'].replace('.py', '')}" for m in matched[:5]])
                await api.edit(message, f"❌ Найдено несколько вариантов, уточните:\n{names}", markdown=True)
                return
            module = matched[0]
        
        await install_module(api, message, module)
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")


async def install_module(api, message, module):
    """Скачивает модуль и устанавливает его в папку modules/."""
    module_name = module['name'].replace('.py', '')
    await api.edit(message, f"⬇️ Устанавливаю **{module_name}**...", markdown=True)
    
    try:
        download_url = f"{RAW_BASE}/{module['path']}"
        file_content = await download_file(download_url)
        
        if not file_content:
            await api.edit(message, "❌ Не удалось скачать файл модуля")
            return
        
        MODULES_DIR.mkdir(exist_ok=True)
        module_path = MODULES_DIR / module['name']
        
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        load_result = await load_module(module_path, api)
        
        size_kb = module.get('size', 0) / 1024
        
        if "успешно загружен" in load_result.lower() or "✅" in load_result:
            await api.edit(
                message,
                f"✅ **Модуль '{module_name}' установлен!**\n\n"
                f"📏 Размер: {size_kb:.1f} KB\n"
                f"📁 Путь: `modules/{module['name']}`\n"
                f"🔄 Статус: загружен и готов к работе\n\n"
                f"📝 {load_result}",
                markdown=True
            )
        else:
            await api.edit(
                message,
                f"⚠️ **Модуль '{module_name}' сохранён, но возникли проблемы при загрузке:**\n\n"
                f"📏 Размер: {size_kb:.1f} KB\n"
                f"📁 Путь: `modules/{module['name']}`\n\n"
                f"📝 {load_result}",
                markdown=True
            )
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка установки: {e}")


async def sr_command(api, message, args):
    """Информация о репозитории."""
    prefix = get_prefix(api)
    info = f"""📂 **Maximus Store**

🔗 {REPO_URL}
📁 {REPO_OWNER}/{REPO_NAME}

**Команды:**
• `{prefix}ss <запрос>` — поиск модулей
• `{prefix}sl` — все модули
• `{prefix}sd <номер/название>` — скачать и установить
• `{prefix}su` — проверить обновления
• `{prefix}sg` — применить ожидающие обновления
• `{prefix}sg y` — обновить всё сразу
• `{prefix}sg n` — отменить ожидающее обновление
• `{prefix}sr` — эта информация

💡 Модули устанавливаются прямо в папку `modules/` и загружаются **без перезапуска бота**."""
    
    await api.edit(message, info, markdown=True)


async def show_results(api, message, modules, search_query):
    """Показывает результаты поиска."""
    prefix = get_prefix(api)
    response = [f"🔍 Найдено по '{search_query}': {len(modules)}\n"]
    response.append(f"📂 {REPO_OWNER}/{REPO_NAME}\n")
    
    for i, module in enumerate(modules, 1):
        name = module['name'].replace('.py', '')
        size_kb = module.get('size', 0) / 1024
        response.append(f"{i}. {name} ({size_kb:.1f} KB)")
    
    response.append(f"\n💾 `{prefix}sd <номер>` — скачать и установить")
    
    if len(modules) == 20:
        response.append("💡 Показано 20 результатов. Уточните запрос.")
    
    await api.edit(message, "\n".join(response), markdown=True)


async def get_repo_modules():
    """Получает все .py файлы из репозитория через github api."""
    try:
        api_url = f"{API_BASE}/contents/"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Maximus-Bot/2.2",
                "Accept": "application/json"
            }
            
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    contents = await response.json()
                    return [item for item in contents if item['type'] == 'file' and item['name'].endswith('.py')]
                return []
                    
    except Exception:
        return []


async def download_file(url):
    """Скачивает содержимое файла."""
    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "Maximus-Bot/2.2"}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
    return None


async def register(api):
    """Регистрирует команды."""
    api.register_command("ss", ss_command)
    api.register_command("sl", sl_command)
    api.register_command("sd", sd_command)
    api.register_command("su", su_command)
    api.register_command("sg", sg_command)
    api.register_command("sr", sr_command)
