from typing import Any, Protocol, Mapping, Iterable, Union

PathLike = Union[str, "os.PathLike[str]"]  # noqa: F821
DfLike = Any  # ne pas imposer pandas ici
JSONMapping = Mapping[str, Any]
