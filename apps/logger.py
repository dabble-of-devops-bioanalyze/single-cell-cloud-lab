import colorlog

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s:%(name)s:%(filename)s:%(funcName)s: %(message)s"
    )
)

logger = colorlog.getLogger(__name__)
logger.addHandler(handler)
