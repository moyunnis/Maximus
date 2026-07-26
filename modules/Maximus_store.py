# name: Maximus Store
# version: 2.0.0
# developer: @moyunni (tg)
# id: maximus_store
# dependencies: aiohttp
# min-Maximus: 100

import aiohttp
import re
import os

REPO_URL = "https://github.com/moyunnis/MaximusStore"
REPO_OWNER = "moyunni"
REPO_NAME = "MaximusStore"

API_BASE = f"https://github.com/api/v1/repos/{REPO_OWNER}/{REPO_NAME}"
RAW_BASE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/raw/branch/main"

async def store_command(api, message, args):
    """Поиск модулей в репозитории Maximus Store."""
    if not args:
        await show_help(api, message)
        return
    
    search_query = " ".join(args).lower()
    await api.edit(message, "🔍 Ищу модули...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, f"❌ Не удалось загрузить модули из репозитория\n📂 {REPO_OWNER}/{REPO_NAME}")
            return
        
        matched = [m for m in modules if search_query in m['name'].lower().replace('.py', '')]
        
        if not matched:
            available = "\n".join([f"• {m['name'].replace('.py', '')}" for m in modules[:10]])
            more = f"\n... и еще {len(modules) - 10}" if len(modules) > 10 else ""
            await api.edit(message, f"❌ Не найдено по запросу: '{search_query}'\n\n📋 Доступные модули:\n{available}{more}\n\n💡 `.sl` - все модули")
            return
        
        if len(matched) == 1:
            await download_module(api, message, matched[0])
        else:
            await show_results(api, message, matched, search_query)
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")

async def ss_command(api, message, args):
    """Быстрый поиск модулей (до 20 результатов)."""
    if not args:
        await api.edit(message, "❌ Укажите запрос: `.ss weather`")
        return
    
    search_query = " ".join(args).lower()
    await api.edit(message, f"🔍 Поиск: '{search_query}'...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, "❌ Не удалось загрузить модули")
            return
        
        matched = [m for m in modules if search_query in m['name'].lower().replace('.py', '')][:20]
        
        if not matched:
            await api.edit(message, f"❌ Не найдено по запросу: '{search_query}'\n\n💡 `.sl` - все модули")
            return
        
        await show_results(api, message, matched, search_query)
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")

async def sl_command(api, message, args):
    """Список всех модулей."""
    await api.edit(message, "📋 Загружаю список...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, "❌ Не удалось загрузить модули")
            return
        
        response = [f"📦 Все модули ({len(modules)}):\n"]
        response.append(f"📂 {REPO_OWNER}/{REPO_NAME}")
        response.append(f"🔗 {REPO_URL}\n")
        
        for i, module in enumerate(modules[:15], 1):
            name = module['name'].replace('.py', '')
            size_kb = module.get('size', 0) / 1024
            response.append(f"{i}. {name} ({size_kb:.1f} KB)")
        
        if len(modules) > 15:
            response.append(f"\n... и еще {len(modules) - 15} модулей")
        
        response.append(f"\n💾 `.sd <номер>` - скачать")
        response.append(f"🔍 `.ss <запрос>` - поиск")
        
        await api.edit(message, "\n".join(response))
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")

async def sd_command(api, message, args):
    """Скачать модуль по номеру."""
    if not args or not args[0].isdigit():
        await api.edit(message, "❌ Укажите номер: `.sd 1`")
        return
    
    module_number = int(args[0])
    await api.edit(message, "🔄 Получаю модуль...")
    
    try:
        modules = await get_repo_modules()
        if not modules:
            await api.edit(message, "❌ Не удалось загрузить модули")
            return
        
        if module_number < 1 or module_number > len(modules):
            await api.edit(message, f"❌ Неверный номер. Доступно: 1-{len(modules)}")
            return
        
        await download_module(api, message, modules[module_number - 1])
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")

async def sr_command(api, message, args):
    """Информация о репозитории."""
    info = f"""📂 **Maximus Store**

🔗 {REPO_URL}
📁 {REPO_OWNER}/{REPO_NAME}

**Команды:**
`.store <название>` - поиск
`.ss <запрос>` - быстрый поиск
`.sl` - все модули
`.sd <номер>` - скачать
`.sr` - эта информация

**Примеры:**
`.store weather` - найти "weather"
`.ss weat` - поиск по части
`.sd 1` - скачать первый"""
    
    await api.edit(message, info, markdown=True)

async def show_help(api, message):
    """Справка по командам."""
    help_text = f"""📦 **Maximus Store**

📂 {REPO_OWNER}/{REPO_NAME}

**Команды:**
`.store <название>` - поиск модулей
`.ss <запрос>` - быстрый поиск (до 20)
`.sl` - все модули
`.sd <номер>` - скачать модуль
`.sr` - информация о репозитории

**Примеры:**
`.store weather` - точный поиск
`.ss weat` - поиск по части
`.sl` - список всех
`.sd 1` - скачать №1"""

    await api.edit(message, help_text, markdown=True)

async def show_results(api, message, modules, search_query):
    """Показывает результаты поиска."""
    response = [f"🔍 Найдено по '{search_query}': {len(modules)}\n"]
    response.append(f"📂 {REPO_OWNER}/{REPO_NAME}\n")
    
    for i, module in enumerate(modules, 1):
        name = module['name'].replace('.py', '')
        size_kb = module.get('size', 0) / 1024
        response.append(f"{i}. {name} ({size_kb:.1f} KB)")
        response.append(f"   💾 `.sd {i}`")
    
    if len(modules) == 20:
        response.append("\n💡 Показано 20 результатов. Уточните запрос.")
    
    await api.edit(message, "\n".join(response))

async def download_module(api, message, module):
    """Скачивает и отправляет модуль."""
    module_name = module['name'].replace('.py', '')
    await api.edit(message, f"⬇️ Скачиваю '{module_name}'...")
    
    try:
        download_url = f"{RAW_BASE}/{module['path']}"
        file_content = await download_file(download_url)
        
        if not file_content:
            await api.edit(message, "❌ Не удалось скачать файл")
            return
        
        temp_filename = f"{module['name']}"
        with open(temp_filename, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        chat_id = message.chat_id
        result = await api.send_file(
            chat_id=chat_id,
            file_path=temp_filename,
            text=f"📦 **{module_name}**\n📂 {REPO_OWNER}/{REPO_NAME}\n⚡ Maximus Store",
            markdown=True
        )
        
        os.remove(temp_filename)
        
        if result:
            await api.delete(message)
        else:
            await api.edit(message, "✅ Скачан, но не удалось отправить")
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {e}")

async def get_repo_modules():
    """Получает все .py файлы из репозитория."""
    try:
        api_url = f"{API_BASE}/contents/"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Maximus-Bot/2.0",
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
        headers = {"User-Agent": "Maximus-Bot/2.0"}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.text()
    return None

async def register(api):
    """Регистрирует команды."""
    api.register_command("store", store_command)
    api.register_command("ss", ss_command)
    api.register_command("sl", sl_command)
    api.register_command("sd", sd_command)
    api.register_command("sr", sr_command)