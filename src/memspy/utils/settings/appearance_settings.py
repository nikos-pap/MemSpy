from dataclasses import dataclass


@dataclass
class AppearanceSettings:
    font_family: str
    search_buttons_font_size: float
    search_table_font_size: float
    search_page_size: int

    pointer_buttons_font_size: float
    pointer_table_font_size: float
    pointer_page_size: int

    workspace_buttons_font_size: float
    workspace_table_font_size: float

