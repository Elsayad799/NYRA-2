from __future__ import annotations
import ast
import operator as op
from datetime import datetime, timezone
from src.tools.telegram_info import TelegramPublicInfo
from src.tools.link_inspector import LinkInspector

_ALLOWED = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
            ast.Mod: op.mod, ast.Pow: op.pow, ast.USub: op.neg, ast.UAdd: op.pos}

def _calc_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
        left, right = _calc_node(node.left), _calc_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 12: raise ValueError("exponent too large")
        return _ALLOWED[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED:
        return _ALLOWED[type(node.op)](_calc_node(node.operand))
    raise ValueError("unsupported expression")

def calculator(expression: str):
    tree = ast.parse(expression, mode="eval")
    return {"result": _calc_node(tree.body)}

def utc_time():
    return {"utc": datetime.now(timezone.utc).isoformat()}

def register_builtins(registry):
    registry.register("calculator", "Safely evaluate basic arithmetic expressions.", calculator)
    registry.register("utc_time", "Get the current UTC time.", utc_time)
    registry.register("telegram_public_info", "Look up a limited public Telegram username profile; excludes phone/access-hash/internal fields.", TelegramPublicInfo.lookup)
    registry.register("inspect_link", "Inspect a URL for status, HTTPS, redirects, content type and basic host information.", LinkInspector.inspect)
