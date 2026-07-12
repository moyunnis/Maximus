import ast
import operator

from core.config import PREFIX


async def uptime_command(api, message, args):
    await api.edit(message, f"⏱ Аптайм: {api.get_uptime()}", markdown=True)


async def id_command(api, message, args):
    chat_id = getattr(message, "chat_id", None)
    sender = getattr(message, "sender", None)

    out = ["🆔 Идентификаторы\n", f"💬 Чат: `{chat_id}`", f"👤 Ты: `{sender}`"]

    reply = getattr(message, "reply_to_message", None)
    if reply:
        if isinstance(reply, dict):
            r_sender, r_id = reply.get("sender"), reply.get("id")
        else:
            r_sender, r_id = getattr(reply, "sender", None), getattr(reply, "id", None)
        if r_sender is not None:
            out.append(f"↩️ Автор реплая: `{r_sender}`")
        if r_id is not None:
            out.append(f"📩 ID реплая: `{r_id}`")

    await api.edit(message, "\n".join(out), markdown=True)


_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _calc(node.left), _calc(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("слишком большая степень")
        return _BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_calc(node.operand))
    raise ValueError("так нельзя")


async def calc_command(api, message, args):
    if not args:
        await api.edit(message, f"⚠️ Пример: `{PREFIX}calc (2 + 3) * 4`", markdown=True)
        return
    expr = " ".join(args)
    try:
        res = _calc(ast.parse(expr, mode="eval"))
        if isinstance(res, float) and res.is_integer():
            res = int(res)
        await api.edit(message, f"🧮 `{expr}` = {res}", markdown=True)
    except ZeroDivisionError:
        await api.edit(message, "❌ Деление на ноль", markdown=True)
    except Exception as e:
        await api.edit(message, f"❌ Не посчитать: {e}", markdown=True)


async def repeat_command(api, message, args):
    if len(args) < 2 or not args[0].isdigit():
        await api.edit(message, f"⚠️ {PREFIX}repeat [число] [текст]", markdown=True)
        return
    count = int(args[0])
    if not 1 <= count <= 50:
        await api.edit(message, "⚠️ От 1 до 50", markdown=True)
        return
    text = " ".join(args[1:])
    chat_id = getattr(message, "chat_id", None) or await api.await_chat_id(message)
    if chat_id is None:
        await api.edit(message, "❌ Не понял чат", markdown=True)
        return
    await api.delete(message)
    for _ in range(count):
        await api.send(chat_id, text)


async def whois_command(api, message, args):
    if args and args[0].lstrip("-").isdigit():
        user_id = int(args[0])
    else:
        reply = getattr(message, "reply_to_message", None)
        user_id = None
        if reply:
            user_id = reply.get("sender") if isinstance(reply, dict) else getattr(reply, "sender", None)
    if user_id is None:
        await api.edit(message, f"⚠️ Реплай или {PREFIX}whois 123", markdown=True)
        return

    await api.edit(message, "🔍 Ищу...", markdown=True)
    info = await api.get_user_info(user_id)
    if not info:
        await api.edit(message, f"❌ Юзер `{user_id}` не найден", markdown=True)
        return

    name = info.names[0].name if getattr(info, "names", None) else "неизвестно"
    out = ["👤 Пользователь\n", f"📛 Имя: {name}", f"🆔 ID: `{user_id}`"]
    phone = getattr(info, "phone", None)
    if phone:
        out.append(f"📱 Телефон: {phone}")
    await api.edit(message, "\n".join(out), markdown=True)


async def register(commands):
    commands["uptime"] = uptime_command
    commands["id"] = id_command
    commands["calc"] = calc_command
    commands["repeat"] = repeat_command
    commands["whois"] = whois_command
