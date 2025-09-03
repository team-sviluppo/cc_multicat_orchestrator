from pydantic import BaseModel
from cat.mad_hatter.decorators import plugin
from enum import Enum


class AvailbleLanguages(Enum):
    it: str = "Italian"
    en: str = "English"


# Plugin settings
class PluginSettings(BaseModel):
    language: AvailbleLanguages = AvailbleLanguages.it
    shared_data: str = ""
    show_agent_why: bool = True


# hook to give the cat settings
@plugin
def settings_schema():
    return PluginSettings.schema()
