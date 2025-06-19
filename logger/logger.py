import inspect
import logging


def create_logger(class_name: str = None, level: int = logging.DEBUG) -> logging.Logger:
    """
    Create and configure a logger with the format:
        "[Classname] LEVEL: message"

    If class_name is omitted, this function attempts to infer the name of the class
    from which it was called (via `self`), falling back to the module name.

    :param class_name: Optional override for the displayed class name.
    :param level: Logging level (e.g., logging.DEBUG, logging.INFO)
    :return: Configured Logger instance
    """
    # Attempt to infer class name if not provided
    if class_name is None:
        display_name = None
        for frame_info in inspect.stack()[1:]:  # skip current frame
            local_self = frame_info.frame.f_locals.get('self')
            if local_self:
                display_name = local_self.__class__.__name__
                break
        if display_name is None:
            # Fallback to module name
            display_name = frame_info.frame.f_globals.get('__name__', '')
    else:
        display_name = class_name

    # Create or retrieve a logger with the chosen name
    logger = logging.getLogger(display_name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(level)

        fmt_string = f"[%(name)s] %(levelname)s: %(message)s"
        formatter = logging.Formatter(fmt_string)
        ch.setFormatter(formatter)

        logger.addHandler(ch)
    return logger


def get_logger(name: str) -> logging.Logger | None:
    """
    Return an existing logger by name, or None if no such logger has been created.

    This function does NOT create a new logger. It inspects the internal
    logging manager's dictionary of loggers and only returns those that
    already exist.

    :param name: The name of the logger to retrieve.
    :return: The Logger instance if it exists, otherwise None.
    """
    # The root logger is always available
    if not name or name == "root":
        return logging.getLogger()

    logger_obj = logging.root.manager.loggerDict.get(name)
    if isinstance(logger_obj, logging.Logger):
        return logger_obj
    return None


def list_all_loggers():
    """
    Print out all registered loggers with their levels and handlers.
    """
    print("=== Registered Loggers ===")
    manager = logging.Logger.manager
    for name, logger_obj in manager.loggerDict.items():
        # Some entries may be PlaceHolder rather than Logger
        if isinstance(logger_obj, logging.Logger):
            handler_names = [type(h).__name__ for h in logger_obj.handlers]
            print(f"{name}: level={logging.getLevelName(logger_obj.level)}, handlers={handler_names}")
        else:
            print(f"{name}: <Placeholder for children>")