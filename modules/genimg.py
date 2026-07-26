# name: Генератор изображений
# version: 1.0.0
# developer: @YouRooni - Maximus Dev
# min-Maximus: 26

import aiohttp
import aiofiles
import os
import asyncio
from core.config import get_module_setting, register_module_settings, save_config, config as core_config

AVAILABLE_MODELS = {
    "1": "flux",
    "2": "turbo",
    "flux": "flux",
    "turbo": "turbo"
}

MODULE_NAME = "genimg"

register_module_settings(MODULE_NAME, {
    "model": {"default": "flux", "description": "Модель генерации (flux/turbo)"},
    "width": {"default": 1024, "description": "Ширина изображения"},
    "height": {"default": 1024, "description": "Высота изображения"},
    "enchant": {"default": True, "description": "Улучшение промпта (enchant)"},
})

def get_setting(key, default=None):
    return get_module_setting(MODULE_NAME, key, default)

def set_setting(key, value):
    conf = core_config
    if "external_modules" not in conf:
        conf["external_modules"] = {}
    if MODULE_NAME not in conf["external_modules"]:
        conf["external_modules"][MODULE_NAME] = {"settings": {}, "descriptions": {}}
    conf["external_modules"][MODULE_NAME]["settings"][key] = value
    save_config(conf)

async def genimg_command(api, message, args):
    """Генерирует изображение по промпту."""
    if not args:
        await api.edit(message, f"🎨 Генератор изображений\n\nИспользование: .genimg [промпт]\nПример: .genimg красивая природа\n\nТекущая модель: {get_setting('model', 'flux')}\nШирина: {get_setting('width', 1024)}\nВысота: {get_setting('height', 1024)}\nEnchant: {get_setting('enchant', True)}")
        return

    prompt = " ".join(args)
    chat_id = getattr(message, 'chat_id', None)
    if not chat_id:
        chat_id = await api.await_chat_id(message)
    if not chat_id:
        await api.edit(message, "❌ Не удалось определить chat_id")
        return

    model = get_setting('model', 'flux')
    width = get_setting('width', 1024)
    height = get_setting('height', 1024)
    enchant = get_setting('enchant', True)

    await api.edit(message, f"🎨 Генерирую изображение...\nПромпт: {prompt}\nМодель: {model}\nРазмер: {width}x{height}\nEnchant: {enchant}")

    try:
        image_url = f"https://pollinations.ai/p/{prompt}?width={width}&height={height}&model={model}&nologo=true&enchant={'true' if enchant else 'false'}"
        print(f"🔍 DEBUG: Генерируем изображение по URL: {image_url}")
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    print(f"✅ Изображение скачано, размер: {len(image_data)} байт")
                    temp_path = f"temp_gen_{message.id}.jpg"
                    async with aiofiles.open(temp_path, 'wb') as f:
                        await f.write(image_data)
                    result = await api.send_photo(
                        chat_id=chat_id,
                        file_path=temp_path,
                        text=f"🎨 Изображение: {prompt}\n🤖 Модель: {model}"
                    )
                    try:
                        os.remove(temp_path)
                        print(f"🧹 Удален временный файл: {temp_path}")
                    except:
                        pass
                    if result:
                        await api.delete(message)
                    else:
                        await api.edit(message, "❌ Ошибка отправки изображения")
                else:
                    await api.edit(message, f"❌ Ошибка генерации: HTTP {response.status}\nВозможно, сервис недоступен")
    except asyncio.TimeoutError:
        await api.edit(message, "⏰ Таймаут генерации изображения\nПопробуйте еще раз или измените промпт")
    except Exception as e:
        await api.edit(message, f"❌ Ошибка: {str(e)}")
        print(f"❌ Ошибка в genimg_command: {e}")

async def genimgmodel_command(api, message, args):
    """Устанавливает модель для генерации изображений."""
    if not args:
        current_model = get_setting('model', 'flux')
        models_text = "🤖 Доступные модели для генерации изображений:\n\n"
        for i, (key, model) in enumerate(AVAILABLE_MODELS.items(), 1):
            if key.isdigit():
                status = "✅" if model == current_model else "⚪"
                models_text += f"{status} {i}. {model}\n"
        models_text += f"\nТекущая модель: **{current_model}**\n"
        models_text += "\nИспользование: .genimgmodel [номер или название]\n"
        models_text += "Примеры: .genimgmodel 1 или .genimgmodel flux"
        await api.edit(message, models_text)
        return

    model_input = args[0].lower()
    if model_input in AVAILABLE_MODELS:
        old_model = get_setting('model', 'flux')
        new_model = AVAILABLE_MODELS[model_input]
        set_setting('model', new_model)
        await api.edit(message, f"✅ Модель изменена: {old_model} → **{new_model}**")
    else:
        await api.edit(message, f"❌ Неизвестная модель: {model_input}\nИспользуйте .genimgmodel для просмотра списка")

async def register(api):
    """Регистрирует команды модуля."""
    api.register_command("genimg", genimg_command)
    api.register_command("genimgmodel", genimgmodel_command)

