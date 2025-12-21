"""Patch built-in print to include module and function name prefixes.

Import this module early in any entry point to prepend `[module.function]`
labels to every console log, which simplifies debugging.
"""

import builtins
import inspect
import threading
from typing import Any

_LOCK = threading.RLock()

if not getattr(builtins, "_print_with_context_active", False):
    _original_print = builtins.print

    def _caller_label() -> str:
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None:
            return "[unknown]"
        wrapper = frame.f_back
        caller = wrapper.f_back
        if caller is None:
            return "[unknown]"
        module = caller.f_globals.get("__name__", "<module>")
        func = caller.f_code.co_name
        return f"[{module}.{func}]"

    def _print_with_context(*args: Any, **kwargs: Any) -> None:
        label = _caller_label()
        with _LOCK:
            _original_print(label, *args, **kwargs)

    builtins.print = _print_with_context  # type: ignore[assignment]
    builtins._print_with_context_active = True  # type: ignore[attr-defined]
