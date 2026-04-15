import os
import sys
from typing import Any, Optional, TextIO


def vd_debug_print(
    custom_prefix: str, *args: Any, sep: str = " ", end: str = "\n", file: Optional[TextIO] = None, flush: bool = False
) -> None:
    """A type-safe wrapper around the built-in print function that handles prefixing."""
    print(custom_prefix, *args, sep=sep, end=end, file=file, flush=flush)


ENV_VAR_BOOLEANNESS = {
    False: ["", "0", "false", "no", "n"],
    True: ["1", "true", "yes", "y"],
}


def get_env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name, "").lower()

    for ret, vals in ENV_VAR_BOOLEANNESS.items():
        if val in vals:
            return ret

    return default
