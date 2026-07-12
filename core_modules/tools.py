import ast
import operator

from core.config import PREFIX


async def uptime_command(api, message, args):
    await api.edit(message, f"🕐 Аптайм: {api.get_uptime()}", markdown=True)


async def id_command(api, message, args):
    chat_id = getattr(message, "chat_id", None)
    sender = getattr(message, "sender", None)

    out = ["🆔 Идентификаторы\n", f"💬 Чат: `{chat_id}`", f"👤 Ты: `{sender}`"]

    reply = api.get_reply(message)
    if reply:
        out.append(f"↩️ Автор реплая: `{reply.get('sender')}`")
        out.append(f"📩 ID реплая: `{reply.get('id')}`")

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


async def register(commands):
    commands["uptime"] = uptime_command
    commands["id"] = id_command
    commands["calc"] = calc_command
