from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


class Result(tuple):
    """Lightweight (ok: bool, msg: str) tuple with safe defaults.

    Tolerant to legacy constructor shapes:
    - Result() -> (False, "")
    - Result(True) -> (True, "")
    - Result((True, "OK")) -> (True, "OK")
    - Result((False,)) -> (False, "")
    - Result(True, "OK") -> (True, "OK")
    """

    __slots__ = ()

    def __new__(cls, *args):
        # Normalize inputs into a 2-tuple (bool, str)
        if not args:
            data = (False, "")
        elif len(args) == 1:
            val = args[0]
            if isinstance(val, tuple):
                if len(val) >= 2:
                    data = (bool(val[0]), str(val[1]))
                elif len(val) == 1:
                    data = (bool(val[0]), "")
                else:
                    data = (False, "")
            else:
                data = (bool(val), "")
        else:
            data = (bool(args[0]), str(args[1]))
        return super().__new__(cls, data)

    @property
    def ok(self) -> bool:
        return bool(self[0])

    @property
    def msg(self) -> str:
        return str(self[1])

@runtime_checkable
class ContextSpec(Protocol):
    """
    Contrat minimal de contexte : config + méta.
    Pas d'implémentation ici, pour rester neutre juridiquement.
    """
    @property
    def cfg(self) -> Mapping[str, Any]: ...
    @property
    def meta(self) -> Mapping[str, Any]: ...
    def set_meta(self, key: str, value: Any) -> None: ...

@runtime_checkable
class Stage(Protocol):
    """
    Un stage exécutable par le pipeline RS3.
    """
    name: str
    def run(self, ctx: ContextSpec) -> Result: ...
