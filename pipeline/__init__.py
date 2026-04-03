# TherapyGraveyard pipeline package
import io
import sys

# ── Windows UTF-8 stdout wrapper (shared, deduplicated) ─────────────
def ensure_utf8_stdout():
    """Wrap stdout with UTF-8 encoding on Windows (guard against double-wrap)."""
    if sys.platform == "win32" and not getattr(sys.stdout, "_tg_utf8", False):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stdout._tg_utf8 = True

# ── Shared constants (single source of truth) ────────────────────────
START_YEAR = 2005
END_YEAR = 2025
N_YEARS = END_YEAR - START_YEAR + 1  # 21
