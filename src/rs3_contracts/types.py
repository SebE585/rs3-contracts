from typing import Any, Mapping, Union

PathLike = Union[str, "os.PathLike[str]"]  # noqa: F821
DfLike = Any  # ne pas imposer pandas ici
JSONMapping = Mapping[str, Any]
