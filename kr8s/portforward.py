from ._io import sync
from ._portforward import PortForward as _PortForward


@sync
class PortForward(_PortForward):
    __doc__ = _PortForward.__doc__
