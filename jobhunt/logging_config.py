import logging

from rich.logging import RichHandler


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with a Rich handler. Never log secrets."""
    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
