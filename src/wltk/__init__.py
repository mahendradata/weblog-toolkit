from importlib.metadata import version

from .logio import parse_log

__version__ = version("wltk")
__all__ = ["parse_log", "__version__"]
