# name: Terminal
# version: 1.0.0
# developer: rorolb
# dependencies: asyncio
# min-Maximus: 26
# id: terminal

import asyncio

async def terminal_command(api, message, args):
    """Выполняет команду в терминале и возвращает результат."""
    if not args:
        await api.edit(message, "❌ Укажите команду для выполнения: .terminal <команда>")
        return
    
    command = " ".join(args)
    
    await api.edit(message, f"🖥️ Выполняю: `{command}`")
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        
        stdout, stderr = await process.communicate()
        
        result = ""
        if stdout:
            stdout_text = stdout.decode('utf-8', errors='ignore')
            result += f"✅ Вывод:\n\n{stdout_text}\n"
        
        if stderr:
            stderr_text = stderr.decode('utf-8', errors='ignore')
            result += f"\n❌ Ошибки:\n\n{stderr_text}\n"
        
        if not result:
            result = "ℹ️ Команда выполнена успешно, вывод пуст"
        
        if len(result) > 4000:
            result = result[:4000] + "\n... (вывод обрезан)"
        
        await api.edit(message, result)
        
    except Exception as e:
        await api.edit(message, f"❌ Ошибка выполнения: {str(e)}")

async def register(api):
    """Регистрирует команды модуля."""
    api.register_command("terminal", terminal_command)
