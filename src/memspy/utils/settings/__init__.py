from memspy.utils.settings.settings import *


def __getattr__(name):
    if name == "CONFIG":
        from memspy.utils.settings.configuration import CONFIG

        return CONFIG

    raise AttributeError(name)
