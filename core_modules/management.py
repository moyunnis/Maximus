from pathlib import Path

from core.loader import load_module, unload_module, LOADED_MODULES
from core.api import MODULES_DIR
from core_modules.modules import fuzzy_find_module
import asyncio
import aiohttp
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile
import tempfile
import datetime
import os
import shutil
from core.config import CONFIG_FILE, config as core_config, save_config

async def load_command(api, message, args):
    await api.edit(message, "❌ Ошибка: эта команда работает только с файлами.\n\nОтправь .py файл и в подписи к нему напиши .load")

async def unload_command(api, message, args):
    if not args:
        await api.edit(message, "⚠️ Укажи имя/номер/часть названия модуля.")
        return
    query = ' '.join(args)
    module, error = fuzzy_find_module(query)
    if not module:
        await api.edit(message, f"❌ {error}")
        return
    
    # Если модуль загружен — выгружаем его
    if module.get('loaded'):
        response = await unload_module(module['name'])
        await api.edit(message, f"Вывод:\n{response}")
    else:
        # Если модуль не загружен, но найден файл — удаляем файл
        try:
            file_path = module['file_path']
            if file_path.exists():
                file_path.unlink()
                await api.edit(message, f"✅ Файл модуля '{module['display_name']}' удален с диска.")
            else:
                await api.edit(message, f"❌ Файл модуля '{module['display_name']}' не найден на диске.")
        except Exception as e:
            await api.edit(message, f"❌ Ошибка удаления файла модуля: {e}")

async def modules_command(api, message, args):
    if not LOADED_MODULES: await api.edit(message, "📦 Нет загруженных модулей."); return
    response = "📦 Загруженные модули:\n\n"
    for name, data in LOADED_MODULES.items():
        ver = data['header'].get('version', 'N/A'); dev = data['header'].get('developer', 'N/A')
        response += f"• {data['header'].get('name', name)} (v{ver}) от {dev}\n"
    await api.edit(message, response)

async def sendmodule_command(api, message, args):
    if not args: await api.edit(message, "⚠️ Укажи имя модуля."); return
    
    # Используем нечеткий поиск для поиска модуля
    module, error = fuzzy_find_module(args[0])
    if not module:
        await api.edit(message, f"❌ {error}")
        return
    
    module_path = module['file_path']
    display_name = module['display_name']
    
    try:
        # Используем chat_id из сообщения
        chat_id = getattr(message, 'chat_id', None)
        if not chat_id:
            await api.edit(message, "❌ Не удалось определить chat_id")
            return
        
        # Отправляем файл модуля
        await api.edit(message, f"⏳ Отправляю файл модуля {display_name}...")
        result = await api.send_file(chat_id, str(module_path), f"Модуль {display_name}", notify=False)
        
        if result:
            await api.delete(message, for_me=False)
        else:
            await api.edit(message, f"❌ Ошибка отправки файла модуля {display_name}")
            
    except Exception as e:
        await api.edit(message, f"❌ Ошибка отправки файла: {e}")

async def register(commands):
    commands["load"] = load_command
    commands["unload"] = unload_command
    commands["modules"] = modules_command
    commands["sendmodule"] = sendmodule_command
    async def reload_command(api, message, args):
        """Перезагружает все внешние модули (файлы в папке modules)."""
        await api.edit(message, "⏳ Перезагрузка внешних модулей...")
        # Сканируем папку MODULES_DIR
        MODULES_DIR.mkdir(exist_ok=True)
        results = []
        for file in MODULES_DIR.glob("*.py"):
            if file.stem == "__init__":
                continue
            module_name = file.stem
            # Пропускаем системные нормализованные имена
            if module_name.endswith("_Maximus"):
                continue
            try:
                res = await load_module(file, api)
                results.append(f"{file.name}: {res}")
            except Exception as e:
                results.append(f"{file.name}: Ошибка {e}")
        text = "\n".join(results) if results else "Нет внешних модулей для перезагрузки"
        await api.edit(message, f"✅ Перезагрузка завершена:\n{text}")

    commands["reload"] = reload_command
    
    async def update_command(api, message, args):
        """Проверяет обновление и обновляет ядро из GitHub."""
        await api.edit(message, "⏳ Проверяю обновления Maximus...")
        
        try:
            # 1) Получаем удалённый api.py (raw)
            raw_url = "https://codeberg.org/moyunni/Maximus/raw/branch/main/core/api.py"
            async with aiohttp.ClientSession() as session:
                async with session.get(raw_url) as resp:
                    if resp.status != 200:
                        await api.edit(message, f"❌ Не удалось получить api.py: HTTP {resp.status}")
                        return
                    remote_api = await resp.text()
            
            # 2) Извлекаем BOT_VERSION_CODE из удалённого файла
            import re
            m = re.search(r"BOT_VERSION_CODE\s*=\s*(\d+)", remote_api)
            if not m:
                await api.edit(message, "❌ Не удалось определить удалённую версию")
                return
            remote_vc = int(m.group(1))
            local_vc = api.BOT_VERSION_CODE
            local_v = api.BOT_VERSION
            
            # 3) Сравниваем
            if local_vc == remote_vc:
                await api.edit(message, f"ℹ️ У вас актуальная версия: v{local_v} ({local_vc})")
                return
            if local_vc > remote_vc:
                await api.edit(message, f"⚠️ У вас версия новее официальной (кастом): {local_vc} > {remote_vc}. Обновление не рекомендуется.")
                return
            
            # 4) Предложение обновиться (если есть арг 'yes' — без вопросов)
            if not args or args[0].lower() not in ("yes", "y", "да"):
                await api.edit(message, f"🔔 Доступна новая версия ({remote_vc} > {local_vc}). Запустите: update yes")
                return
            
            # 5) Обновляем из Git, не трогая конфиги/модули/сессию
            await api.edit(message, "🔄 Начинаю обновление с GitHub...")
            repo_url = "https://codeberg.org/moyunni/Maximus.git"
            project_root = Path.cwd()
            temp_dir = project_root / "_update_tmp"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Клонируем во временную папку (только чистые системные директории)
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gitpython"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            from git import Repo
            Repo.clone_from(repo_url, str(temp_dir))
            
            # Список системных путей для обновления (не трогаем modules/, pymax_session/, Maximus_config.json)
            preserve = {"modules", "pymax_session", "Maximus_config.json", ".git", ".gitignore"}
            copy_roots = ["core", "core_modules", "pymax", "main.py", "install_linux.sh", "install_windows.bat", "README.md"]
            
            import shutil
            for item in copy_roots:
                src = temp_dir / item
                dst = project_root / item
                if src.exists():
                    if src.is_dir():
                        # Удаляем старую директорию перед копированием
                        if dst.exists():
                            shutil.rmtree(dst, ignore_errors=True)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
            
            # Удаляем временную директорию
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 6) Сообщаем и перезапускаем процесс (используем уже существующий механизм restart)
            await api.edit(message, "✅ Обновление установлено. Перезапуск...")
            # Переиспользуем логику перезапуска
            from core_modules.restart import restart_command
            await restart_command(api, message, ["Обновление Maximus"])
            
        except Exception as e:
            await api.edit(message, f"❌ Ошибка обновления: {e}")

    commands["update"] = update_command

    async def exportlog_command(api, message, args):
        """Экспорт последних N строк логов в файл и отправка."""
        count = 200
        if args and args[0].isdigit():
            count = max(1, min(5000, int(args[0])))
        await api.edit(message, f"⏳ Готовлю {count} строк логов...")
        try:
            lines = api.LOG_BUFFER[-count:] if hasattr(api, 'LOG_BUFFER') else []
            content = "\n".join(lines)
            ts = int(time.time())
            file_path = Path(f"log_{count}_{ts}.txt")
            file_path.write_text(content, encoding='utf-8')
            chat_id = getattr(message, 'chat_id', None) or await api.await_chat_id(message)
            if chat_id:
                await api.send_file(chat_id, str(file_path), f"Логи ({count} строк)", notify=False)
                await api.delete(message, for_me=False)
            else:
                await api.edit(message, f"✅ Лог сохранён: {file_path}")
        except Exception as e:
            await api.edit(message, f"❌ Ошибка экспорта логов: {e}")

    commands["exportlog"] = exportlog_command

    # Простая очередь для хранящихся загруженных бэкапов перед применением
    PENDING_BACKUPS = {}
    
    async def backup_command(api, message, args):
        """Создаёт zip-архив с конфигом (без номера телефона), всеми файлами из modules/ и доп.файлами модулей (.json/.db).
        В архив добавляется meta.json с метаданными: author, date, module_count, modules
        """
        snippet = getattr(message, 'text', '')
        api.LOG_BUFFER.append(f"[backup] {snippet[:80]}")
        api.LOG_BUFFER.append(f"[backup-full] {getattr(message, 'text', '')}")
        await api.edit(message, "⏳ Готовлю бэкап...")
        try:
            # Подготовка временного файла
            ts = int(time.time())
            tmp_name = f"backup_{ts}.zip"
            tmp_path = Path(tmp_name)

            def make_backup():
                # 1) Сохраняем конфиг без phone во временный файл
                conf_copy = dict(core_config)
                conf_copy.pop('phone', None)
                config_tmp_path = Path("Maximus_config.json")
                with open(config_tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(conf_copy, f, ensure_ascii=False, indent=2)
                with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as z:
                    # 1) добавляем Maximus_config.json
                    z.write(config_tmp_path, 'Maximus_config.json')
                    # 2) модули и любые файлы в папке MODULES_DIR
                    MODULES_DIR.mkdir(exist_ok=True)
                    modules = []
                    for p in MODULES_DIR.rglob('*'):
                        if p.is_file():
                            arcname = os.path.join('modules', os.path.relpath(p, MODULES_DIR))
                            z.write(p, arcname)
                            modules.append(str(p.name))
                    # 3) (опционально) другие файлы - пока не добавляем глобальные session
                    meta = {
                        'author': getattr(api.me, 'names', None) and api.me.names[0].name or str(getattr(message, 'sender', 'unknown')),
                        'date': datetime.datetime.utcnow().isoformat() + 'Z',
                        'module_count': len(modules),
                        'modules': modules,
                    }
                    z.writestr('meta.json', json.dumps(meta, ensure_ascii=False, indent=2))
                # Удаляем временный Maximus_config.json
                try:
                    config_tmp_path.unlink()
                except Exception:
                    pass
            await asyncio.to_thread(make_backup)

            # Отправляем архив
            chat_id = getattr(message, 'chat_id', None) or await api.await_chat_id(message)
            if chat_id:
                await api.send_file(chat_id, str(tmp_path), f"Backup {ts}", notify=False)
                await api.delete(message, for_me=False)

            # Удаляем временный файл
            try:
                tmp_path.unlink()
            except Exception:
                pass

        except Exception as e:
            err_text = f"❌ Ошибка создания бэкапа: {e} | Сообщение: {getattr(message, 'text', '')}"
            try:
                from core.api import _append_log
                _append_log(err_text)
            except Exception:
                api.LOG_BUFFER.append(err_text)
            await api.edit(message, err_text)

    commands['backup'] = backup_command

    async def loadbackup_command(api, message, args):
        """Загружает zip-бекап из прикреплённого файла, показывает meta.json и просит подтвердить восстановление.
        Для подтверждения используйте: loadbackup apply <id>
        """
        # 2 режима: если есть args and args[0]=='apply' — применять; иначе — считать прикреплённый zip и показать мету
        if args and args[0].lower() == 'apply':
            # apply pending
            key = args[1] if len(args) > 1 else None
            if not PENDING_BACKUPS:
                await api.edit(message, "⚠️ Нет ожидающих бэкапов для применения.")
                return
            if key is None:
                if len(PENDING_BACKUPS) == 1:
                    key = next(iter(PENDING_BACKUPS.keys()))
                else:
                    await api.edit(message, f"⚠️ Укажите id бэкапа. Доступны: {', '.join(PENDING_BACKUPS.keys())}")
                    return

            info = PENDING_BACKUPS.get(key)
            if not info:
                await api.edit(message, f"❌ Бэкап {key} не найден или истёк.")
                return

            await api.edit(message, f"⏳ Применяю бэкап {key} — выполняется восстановление...")

            def apply_backup():
                tmp_zip = info['path']
                extract_dir = Path(tempfile.mkdtemp(prefix='Maximus_backup_'))
                try:
                    with zipfile.ZipFile(tmp_zip, 'r') as z:
                        z.extractall(extract_dir)

                    # 1) Восстановление конфигурации (не трогаем phone)
                    cfg_path = extract_dir / 'Maximus_config.json'
                    if cfg_path.exists():
                        with open(cfg_path, 'r', encoding='utf-8') as f:
                            new_conf = json.load(f)
                        # Сохраняем телефон и сессию
                        current_phone = core_config.config.get('phone')
                        new_conf['phone'] = current_phone
                        # Сохраняем конфиг в файл
                        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                            json.dump(new_conf, f, indent=4, ensure_ascii=False)
                        # Обновляем объект в памяти
                        core_config.config = new_conf

                    # 2) Восстановление модулей: копируем файлы из extracted modules/ -> MODULES_DIR
                    src_modules = extract_dir / 'modules'
                    if src_modules.exists():
                        MODULES_DIR.mkdir(exist_ok=True)
                        for root, dirs, files in os.walk(src_modules):
                            rel = os.path.relpath(root, src_modules)
                            for fn in files:
                                srcf = Path(root) / fn
                                if rel == '.':
                                    dest = MODULES_DIR / fn
                                else:
                                    dest_dir = MODULES_DIR / rel
                                    dest_dir.mkdir(parents=True, exist_ok=True)
                                    dest = dest_dir / fn
                                shutil.copy2(srcf, dest)

                    return True, None
                except Exception as e:
                    return False, str(e)
                finally:
                    # Удаляем времечную директорию
                    try:
                        shutil.rmtree(extract_dir)
                    except Exception:
                        pass

            ok, err = await asyncio.to_thread(apply_backup)
            # После применения — удаляем pending и временный zip
            try:
                Path(info['path']).unlink()
            except Exception:
                pass
            del PENDING_BACKUPS[key]

            if not ok:
                await api.edit(message, f"❌ Ошибка при применении бэкапа: {err}")
                return

            # Перезагрузим внешние модули
            MODULES_DIR.mkdir(exist_ok=True)
            results = []
            for file in MODULES_DIR.glob("*.py"):
                if file.stem == "__init__":
                    continue
                try:
                    res = await load_module(file, api)
                    results.append(f"{file.name}: {res}")
                except Exception as e:
                    results.append(f"{file.name}: Ошибка {e}")

            await api.edit(message, f"✅ Восстановление завершено. Перезагрузка модулей:\n{"\n".join(results)}")
            return

        # Иначе — ожидаем zip во вложении
        attach = getattr(message, 'attaches', None)
        
        # Если нет attach, пробуем найти файл в ответе на сообщение (как в modules.py)
        if not attach:
            print("🔍 DEBUG: В текущем сообщении нет вложений, проверяем reply_to_message...")
            if hasattr(message, 'reply_to_message') and message.reply_to_message:
                reply_msg = message.reply_to_message
                print(f"🔍 DEBUG: Обнаружен ответ на сообщение, проверяем вложения...")
                
                if isinstance(reply_msg, dict):
                    # reply_to_message это словарь
                    reply_attaches = reply_msg.get('attaches', [])
                    if reply_attaches:
                        print("🔍 DEBUG: В исходном сообщении есть вложения (dict), используем их...")
                        attach = reply_attaches
                    else:
                        print("🔍 DEBUG: В исходном сообщении (dict) нет вложений")
                else:
                    # reply_to_message это объект
                    if hasattr(reply_msg, 'attaches') and reply_msg.attaches:
                        print("🔍 DEBUG: В исходном сообщении есть вложения (object), используем их...")
                        attach = reply_msg.attaches
                    else:
                        print("🔍 DEBUG: В исходном сообщении (object) нет вложений")
            else:
                print("🔍 DEBUG: Нет reply_to_message")
        
        if not attach:
            await api.edit(message, "⚠️ Прикрепите zip-файл с бэкапом к сообщению или ответьте на сообщение с файлом и вызовите loadbackup.")
            return

        try:
            attach0 = attach[0]
            print(f"🔍 DEBUG: attach0 = {attach0}")
            print(f"🔍 DEBUG: type(attach0) = {type(attach0)}")
            
            # Обрабатываем как словарь и как объект
            if isinstance(attach0, dict):
                name = attach0.get('name', 'backup.zip')
                file_id = attach0.get('fileId')
                token = attach0.get('token')
                url = attach0.get('url')  # Может быть None
                print(f"🔍 DEBUG: dict - name={name}, fileId={file_id}, token={token}, url={url}")
                
                # Если нет прямого URL, генерируем его из fileId и token
                if not url and file_id and token:
                    url = f"https://files.oneme.ru/{file_id}/{token}"
                    print(f"🔍 DEBUG: Сгенерирован URL: {url}")
            else:
                url = getattr(attach0, 'url', None)
                name = getattr(attach0, 'name', 'backup.zip')
                file_id = getattr(attach0, 'fileId', None)
                token = getattr(attach0, 'token', None)
                print(f"🔍 DEBUG: object - url={url}, name={name}, fileId={file_id}, token={token}")
                
                # Если нет прямого URL, генерируем его из fileId и token
                if not url and file_id and token:
                    url = f"https://files.oneme.ru/{file_id}/{token}"
                    print(f"🔍 DEBUG: Сгенерирован URL: {url}")
            
            if not url:
                await api.edit(message, "❌ Ошибка: не удалось получить URL файла (нет fileId/token или url).")
                return
                
            if not name.lower().endswith('.zip'):
                await api.edit(message, f"❌ Ошибка: файл '{name}' не является zip-архивом.")
                return
                
            print(f"🔍 DEBUG: Файл принят - {name} ({url})")

            await api.edit(message, "⏳ Скачиваю бэкап для проверки...")

            tmpf = Path(tempfile.mktemp(suffix='.zip'))

            # Используем API для получения URL файла
            try:
                if isinstance(attach0, dict):
                    file_id = attach0.get('fileId')
                    token = attach0.get('token')
                else:
                    file_id = getattr(attach0, 'fileId', None)
                    token = getattr(attach0, 'token', None)
                
                if file_id and token:
                    # Получаем URL через API
                    file_url = await api.get_file_url(file_id, token, message.id, chat_id)
                    if not file_url:
                        await api.edit(message, "❌ Не удалось получить URL файла через API.")
                        return
                    print(f"🔍 DEBUG: Получен URL через API: {file_url}")
                    url = file_url
            except Exception as e:
                print(f"⚠️ Ошибка получения URL через API: {e}, используем прямой URL")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await api.edit(message, f"❌ Не удалось скачать файл: HTTP {resp.status}")
                        return
                    data = await resp.read()
                    tmpf.write_bytes(data)

            # Прочитаем meta.json
            try:
                with zipfile.ZipFile(tmpf, 'r') as z:
                    if 'meta.json' not in z.namelist():
                        await api.edit(message, "❌ В архиве нет meta.json — это не валидный бэкап.")
                        tmpf.unlink(missing_ok=True)
                        return
                    meta = json.loads(z.read('meta.json').decode('utf-8'))
            except Exception as e:
                await api.edit(message, f"❌ Ошибка при чтении архива: {e}")
                tmpf.unlink(missing_ok=True)
                return

            # Сохраним pending
            b_id = f"b{int(time.time())}"
            PENDING_BACKUPS[b_id] = {'path': str(tmpf), 'meta': meta, 'uploader': getattr(message, 'sender', None)}

            info_text = f"🗂 Бэкап принят: id={b_id}\nАвтор: {meta.get('author')}\nДата: {meta.get('date')}\nМодулей: {meta.get('module_count')}\n\nДля восстановления отправьте: loadbackup apply {b_id}"
            await api.edit(message, info_text)

        except Exception as e:
            await api.edit(message, f"❌ Ошибка обработки файла: {e}")

    commands['loadbackup'] = loadbackup_command
