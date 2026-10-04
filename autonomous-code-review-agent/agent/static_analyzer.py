"""Built-in static analyzer. Works offline with zero external services.

Python files get deep AST analysis; JS/TS get regex rules; every language gets secret/TODO scanning.
"""
import ast
import re
from typing import Dict, List, Optional

from .models import Issue
from .rules import RULES

PY_EXT = (".py",)
JS_EXT = (".js", ".jsx", ".ts", ".tsx")
SCAN_EXT = PY_EXT + JS_EXT + (".java", ".go", ".rb", ".php", ".cs")

SECRET_RE = re.compile(
    r"""(?ix)(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|token)
        ['"]?\s*[:=]\s*(['"])([^'"\s]{6,})\2""")
AWS_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
PLACEHOLDER_RE = re.compile(r"(?i)(your[_-]|example|placeholder|<.*>|xxx|\$\{|%\()")
TODO_RE = re.compile(r"(#|//|/\*)\s*.*\b(TODO|FIXME|HACK)\b")
JS_EVAL_RE = re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(")
JS_HTML_RE = re.compile(r"\.innerHTML\s*=|\.outerHTML\s*=|document\.write\s*\(")

MAX_COMPLEXITY = 10
MAX_FUNC_LINES = 50


def make_snippet(lines: List[str], line: int, context: int = 2) -> str:
    if line <= 0 or not lines:
        return ""
    start, end = max(1, line - context), min(len(lines), line + context)
    return "\n".join(f"{n:>4} | {lines[n - 1]}" for n in range(start, end + 1))


def _issue(rule: str, path: str, line: int, lines: List[str], message: Optional[str] = None) -> Issue:
    r = RULES[rule]
    return Issue(
        file=path, line=line, severity=r["severity"], category=r["category"], rule=rule,
        message=message or r["title"], source="builtin", explanation=r["explanation"],
        suggested_fix=r["fix"], snippet=make_snippet(lines, line),
    )


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_const(node: Optional[ast.AST], value) -> bool:
    return isinstance(node, ast.Constant) and node.value is value


def _dynamic_str(node: ast.AST) -> bool:
    """True if the expression builds a string from non-constant parts (f-string, +, %, .format)."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        has_str = any(isinstance(n, ast.Constant) and isinstance(n.value, str) for n in ast.walk(node))
        all_const = isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant)
        return has_str and not all_const
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return isinstance(node.func.value, ast.Constant) and bool(node.args or node.keywords)
    return False


def _complexity(func: ast.AST) -> int:
    score = 1
    for n in ast.walk(func):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            score += 1 + len(n.ifs)
    return score


def _analyze_python(path: str, src: str, lines: List[str]) -> List[Issue]:
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [_issue("PY-SYNTAX", path, exc.lineno or 1, lines, f"Syntax error: {exc.msg}")]

    out: List[Issue] = []

    def add(rule: str, node: ast.AST, msg: Optional[str] = None) -> None:
        out.append(_issue(rule, path, getattr(node, "lineno", 0), lines, msg))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _dotted(node.func)
            kws = {k.arg: k.value for k in node.keywords if k.arg}
            if name in ("eval", "exec") and node.args and not isinstance(node.args[0], ast.Constant):
                add("PY-EVAL", node, f"Use of {name}() on dynamic input")
            elif name in ("os.system", "os.popen"):
                add("PY-SHELL", node, f"{name}() runs a shell command")
            elif name.startswith("subprocess.") and _is_const(kws.get("shell"), True):
                add("PY-SHELL", node, f"{name}() called with shell=True")
            elif name in ("pickle.load", "pickle.loads", "marshal.load", "marshal.loads", "cPickle.loads"):
                add("PY-PICKLE", node, f"Unsafe deserialization with {name}()")
            elif name == "yaml.load" and "Loader" not in kws and len(node.args) < 2:
                add("PY-YAML", node)
            elif name in ("hashlib.md5", "hashlib.sha1"):
                add("PY-WEAKHASH", node, f"Weak hash algorithm: {name}")
            if name.split(".")[-1] in ("execute", "executemany", "executescript") and node.args \
                    and _dynamic_str(node.args[0]):
                add("PY-SQLI", node)
            if _is_const(kws.get("verify"), False):
                add("PY-TLS", node)
            if name.endswith(".run") and _is_const(kws.get("debug"), True):
                add("PY-DEBUG", node)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
            for d in defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)) or \
                        (isinstance(d, ast.Call) and _dotted(d.func) in ("list", "dict", "set")):
                    add("PY-MUTABLE-DEFAULT", d, f"Mutable default argument in '{node.name}()'")
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > MAX_FUNC_LINES:
                add("PY-LONG-FUNC", node, f"Function '{node.name}' is {length} lines long (limit {MAX_FUNC_LINES})")
            cx = _complexity(node)
            if cx > MAX_COMPLEXITY:
                add("PY-COMPLEXITY", node,
                    f"Function '{node.name}' has cyclomatic complexity {cx} (limit {MAX_COMPLEXITY})")

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                add("PY-BARE-EXCEPT", node)
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                add("PY-SWALLOW", node)

        elif isinstance(node, (ast.For, ast.While)):
            it = getattr(node, "iter", None)
            if isinstance(it, ast.Call) and _dotted(it.func) == "range" and len(it.args) == 1 \
                    and isinstance(it.args[0], ast.Call) and _dotted(it.args[0].func) == "len":
                add("PY-RANGELEN", node)
            for inner in ast.walk(node):
                if isinstance(inner, ast.AugAssign) and isinstance(inner.op, ast.Add) and (
                        isinstance(inner.value, ast.JoinedStr)
                        or (isinstance(inner.value, ast.Constant) and isinstance(inner.value.value, str))):
                    add("PY-STRCONCAT", inner)

    # unused imports (skipped for package __init__ re-exports)
    if not path.endswith("__init__.py"):
        imported: Dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported.setdefault((a.asname or a.name).split(".")[0], node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
                for a in node.names:
                    if a.name != "*":
                        imported.setdefault(a.asname or a.name, node.lineno)
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        used |= {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for name, lineno in imported.items():
            if name not in used:
                out.append(_issue("PY-UNUSED-IMPORT", path, lineno, lines, f"'{name}' is imported but never used"))
    return out


def _analyze_lines(path: str, lines: List[str]) -> List[Issue]:
    out: List[Issue] = []
    is_js = path.lower().endswith(JS_EXT)
    for i, line in enumerate(lines, 1):
        m = SECRET_RE.search(line)
        if m and not PLACEHOLDER_RE.search(m.group(3)):
            out.append(_issue("SECRET", path, i, lines, f"Hard-coded {m.group(1).lower()} in source code"))
        elif AWS_RE.search(line):
            out.append(_issue("SECRET", path, i, lines, "Hard-coded AWS access key id"))
        if TODO_RE.search(line):
            out.append(_issue("TODO", path, i, lines))
        if is_js:
            if JS_EVAL_RE.search(line):
                out.append(_issue("JS-EVAL", path, i, lines))
            if JS_HTML_RE.search(line):
                out.append(_issue("JS-INNERHTML", path, i, lines))
    return out


def analyze_source(path: str, src: str) -> List[Issue]:
    """Analyze one file and return de-duplicated issues sorted by line."""
    lines = src.splitlines()
    found: List[Issue] = []
    if path.lower().endswith(PY_EXT):
        found += _analyze_python(path, src, lines)
    found += _analyze_lines(path, lines)
    seen, unique = set(), []
    for i in found:
        key = (i.file, i.line, i.rule)
        if key not in seen:
            seen.add(key)
            unique.append(i)
    return sorted(unique, key=lambda i: (i.line, i.rule))
