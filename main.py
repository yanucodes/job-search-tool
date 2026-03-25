"""Command-line interface for job search."""

import search


def display_menu(menu):
    """Display numbered menu options.

    Args:
        menu: Dictionary mapping keys to tuples of label and callable.
    """
    for key, (label, _) in menu.items():
        print(f"{key}. {label}")


def handle_menu_choice(choice, menu):
    """Call the function associated with a menu option.

    Args:
        choice: Key of the selected menu option.
        menu: Dictionary mapping keys to tuples of label and callable.
    """
    if choice in menu:
        menu[choice][1]()
    else:
        print("Invalid choice.")


def add_config():
    """Prompt the user to select a search service and add a configuration."""
    print("Available search services:")
    for service in search.SERVICES:
        print(service)
    service = input("Which service would you like to use? ")
    search.add_config(service)


def display_configs():
    """Display saved search configurations."""
    configs = search.load_config()
    if len(configs) == 0:
        print("No configurations set up yet.")
    else:
        for i, config in enumerate(configs):
            print(f"{i+1}. Configuration for {config['service']}:")
            print(f"   {config['config']}")


def select_config():
    """Prompt the user to select a configuration by index.

    Returns:
        Index of the selected configuration, or None if the user cancels.
    """
    configs = search.load_config()
    print("0. Cancel")
    while True:
        choice = input("Select a configuration by number: ")
        if choice.isdigit():
            choice = int(choice)
            if not choice:
                return None
            elif 0 < choice <= len(configs):
                return choice - 1
        print("Invalid choice.")


def update_config():
    """Prompt the user to select and update a search configuration."""
    display_configs()
    index = select_config()
    if index is not None:
        search.update_config(index)


def remove_config():
    """Prompt the user to select and remove a search configuration."""
    display_configs()
    index = select_config()
    if index is not None:
        search.remove_config(index)


def show_config_menu():
    """Display saved configurations and the configuration menu."""
    display_configs()
    display_menu(CONFIG_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(choice, CONFIG_MENU)


MAIN_MENU = {
    "1": ("Show search configurations", show_config_menu)
}

CONFIG_MENU = {
    "1": ("Add configuration", add_config),
    "2": ("Update configuration", update_config),
    "3": ("Remove configuration", remove_config),
}


def main():
    """Display the main menu and handle user input."""
    display_menu(MAIN_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(choice, MAIN_MENU)


if __name__ == "__main__":
    main()