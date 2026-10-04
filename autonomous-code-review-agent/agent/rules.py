"""Built-in rule library: severity, category, plain-English explanation and a fix for every rule.

This is what lets the agent explain and suggest fixes even when no LLM is available.
"""

RULES = {
    "PY-SYNTAX": dict(
        severity="CRITICAL", category="bug", title="Python syntax error",
        explanation="The file cannot be parsed, so it will crash on import and no other analysis is possible.",
        fix="Fix the syntax at the reported line (missing colon/bracket/quote or bad indentation are the usual causes)."),
    "PY-EVAL": dict(
        severity="CRITICAL", category="security", title="Use of eval()/exec() on dynamic input",
        explanation="eval/exec run arbitrary Python. If any part of the input is attacker-controlled this is remote code execution.",
        fix="Use ast.literal_eval(value) for data, json.loads() for JSON, or a dict of allowed operations:\n"
            "OPS = {'add': operator.add, 'sub': operator.sub}\nresult = OPS[name](a, b)"),
    "PY-SHELL": dict(
        severity="CRITICAL", category="security", title="Shell command execution",
        explanation="Commands run through a shell (os.system, shell=True) allow command injection when any argument comes from user input.",
        fix="Pass an argument list and no shell:\nsubprocess.run(['ping', '-c', '1', host], check=True, capture_output=True, timeout=10)"),
    "PY-SQLI": dict(
        severity="CRITICAL", category="security", title="SQL query built with string formatting (SQL injection)",
        explanation="Building SQL with f-strings, +, % or .format() lets user input change the query, enabling data theft or deletion.",
        fix="Use a parameterized query:\ncursor.execute('SELECT * FROM users WHERE name = ?', (name,))  # use %s for psycopg2/MySQL"),
    "SECRET": dict(
        severity="CRITICAL", category="security", title="Hard-coded secret or credential",
        explanation="Secrets committed to source control are exposed to everyone with repository access and remain in git history.",
        fix="Read secrets from the environment or a secrets manager: API_KEY = os.environ['API_KEY']. "
            "Then rotate the leaked value, because it must be treated as compromised."),
    "PY-PICKLE": dict(
        severity="MAJOR", category="security", title="Unsafe deserialization (pickle/marshal)",
        explanation="Unpickling data can execute arbitrary code. Never unpickle data from an untrusted source.",
        fix="Use a safe format such as JSON (json.loads) or validate/sign the data before loading it."),
    "PY-YAML": dict(
        severity="MAJOR", category="security", title="yaml.load without a safe loader",
        explanation="yaml.load with the default loader can construct arbitrary Python objects from the document.",
        fix="Use yaml.safe_load(stream)."),
    "PY-WEAKHASH": dict(
        severity="MAJOR", category="security", title="Weak hash algorithm (MD5/SHA-1)",
        explanation="MD5 and SHA-1 are broken for security use; they are unsuitable for passwords or integrity checks.",
        fix="Use hashlib.sha256 for integrity; for passwords use a slow salted hash such as bcrypt, scrypt or argon2."),
    "PY-TLS": dict(
        severity="MAJOR", category="security", title="TLS certificate verification disabled",
        explanation="verify=False makes HTTPS requests vulnerable to man-in-the-middle attacks.",
        fix="Remove verify=False. If you use a private CA, pass verify='/path/to/ca-bundle.pem'."),
    "PY-DEBUG": dict(
        severity="MAJOR", category="security", title="Debug mode enabled",
        explanation="Debug mode exposes an interactive debugger and stack traces; on a public server it allows code execution.",
        fix="app.run(debug=os.environ.get('FLASK_DEBUG') == '1') and serve production with gunicorn."),
    "PY-BARE-EXCEPT": dict(
        severity="MAJOR", category="bug", title="Bare 'except:' clause",
        explanation="A bare except also catches KeyboardInterrupt/SystemExit and hides real bugs.",
        fix="Catch specific exceptions:\ntry:\n    ...\nexcept (ValueError, KeyError) as exc:\n    logger.warning('failed: %s', exc)"),
    "PY-SWALLOW": dict(
        severity="MAJOR", category="bug", title="Exception silently ignored",
        explanation="An except block containing only 'pass' discards the error, so failures go unnoticed and are very hard to debug.",
        fix="Handle the error or at least log it: logger.exception('operation failed'); re-raise if you cannot recover."),
    "PY-MUTABLE-DEFAULT": dict(
        severity="MAJOR", category="bug", title="Mutable default argument",
        explanation="The default object is created once and shared across all calls, so data leaks between calls.",
        fix="Use None as the default:\ndef add(item, items=None):\n    items = [] if items is None else items"),
    "PY-COMPLEXITY": dict(
        severity="MAJOR", category="quality", title="Function is too complex",
        explanation="High cyclomatic complexity means many execution paths, which makes the function hard to test and easy to break.",
        fix="Split the function into smaller helpers, use early returns, and replace long if/elif chains with a lookup table."),
    "PY-LONG-FUNC": dict(
        severity="MINOR", category="quality", title="Function is too long",
        explanation="Long functions mix several responsibilities and are hard to read, test and reuse.",
        fix="Extract cohesive blocks into well-named helper functions (aim for under ~50 lines)."),
    "PY-UNUSED-IMPORT": dict(
        severity="MINOR", category="quality", title="Unused import",
        explanation="Unused imports add noise, slow start-up slightly and can hide missing dependencies.",
        fix="Remove the import."),
    "PY-RANGELEN": dict(
        severity="INFO", category="performance", title="range(len(...)) loop",
        explanation="Indexing through range(len(x)) is slower to read and error-prone compared with direct iteration.",
        fix="for index, item in enumerate(items):  # or: for item in items:"),
    "PY-STRCONCAT": dict(
        severity="MINOR", category="performance", title="String concatenation inside a loop",
        explanation="Repeated += on strings creates a new string every iteration (quadratic time for large loops).",
        fix="Collect parts in a list and join once: ''.join(parts)"),
    "JS-EVAL": dict(
        severity="CRITICAL", category="security", title="Use of eval() / new Function",
        explanation="eval executes arbitrary JavaScript and enables code injection.",
        fix="Parse data with JSON.parse() and use explicit logic instead of evaluating strings."),
    "JS-INNERHTML": dict(
        severity="MAJOR", category="security", title="Assignment to innerHTML / document.write (XSS)",
        explanation="Inserting unsanitised strings as HTML allows cross-site scripting.",
        fix="Use element.textContent = value, or sanitize with a library such as DOMPurify before inserting HTML."),
    "TODO": dict(
        severity="INFO", category="quality", title="Unresolved TODO/FIXME comment",
        explanation="Marker comments often indicate unfinished or known-broken code that should be tracked.",
        fix="Resolve it or convert it into a tracked issue and reference the ticket number."),
}
