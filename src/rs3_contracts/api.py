from __future__ import annotations
from typing import Protocol, runtime_checkable, Any, Mapping

class Result(tuple):
    """
    Tuple (ok: bool, msg: str) minimal et stable pour le pipeline.
    """
    __slots__ = ()
    @property
    def ok(self) -> bool: return bool(self[0])
    @property
    def msg(self) -> str: return str(self[1])

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
