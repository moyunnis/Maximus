# name: Markdowner
# version: 1.0.0
# developer: @YouRooni
# id: markdowner
# min-Maximus: 34

async def markdown_command(api, message, args):
    """Редактирует сообщение, применяя к нему Markdown форматирование."""
    
    if not args:
        await api.edit(message, "⚠️ **Ошибка:** Вы не ввели текст для форматирования.", markdown=True)
        return

    text_to_format = " ".join(args)

    try:
        await api.edit(message, text_to_format, markdown=True)
    except Exception as e:
        error_text = f"❌ **Ошибка форматирования Markdown:**\n`{str(e)}`"
        await api.edit(message, error_text, markdown=True)
        api.LOG_BUFFER.append(f"[markdowner_error] {str(e)}")


async def register(api):
    """Регистрирует команду в боте."""
    api.register_command("md", markdown_command)
