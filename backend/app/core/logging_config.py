import logging
import sys


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configures application logging.
    Guarantees privacy: Never logs raw resume text, job description text, or PII.
    Only logs operational metadata (file size, extraction duration, score summary).
    """
    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("ats_checker")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()
