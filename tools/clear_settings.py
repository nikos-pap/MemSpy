from PyQt6.QtCore import QSettings


def show_settings(organization: str = "Uminode", application: str = "MemSpy") -> None:
    """Display all settings for the given organization and application."""
    settings = QSettings(organization, application)
    keys = settings.allKeys()

    if not keys:
        print(f"No settings found for [{organization}/{application}].")
        return

    print(f"Settings for [{organization}/{application}]:")
    for key in keys:
        value = settings.value(key)
        print(f"  {key} = {value!r}")


def clear_settings(organization: str = "Uminode", application: str = "MemSpy") -> None:
    """Clear all settings for the given organization and application."""
    settings = QSettings(organization, application)
    settings.clear()
    settings.sync()
    print(f"All settings for [{organization}/{application}] cleared.")


if __name__ == "__main__":
    # Example usage:
    print("Current settings:")
    # show_settings("MyCompany", "MyApp")
    show_settings()

    # Uncomment to clear old data
    # clear_settings("MyCompany", "MyApp")
    clear_settings()
