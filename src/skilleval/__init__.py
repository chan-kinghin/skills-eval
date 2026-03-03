"""SkillEval: Find the cheapest model that gets your task 100% right."""

try:
    from skilleval._version import __version__
except ModuleNotFoundError:  # editable install without build
    __version__ = "0.0.0.dev0"
