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
    """Display saved search configurations and show the configuration menu."""
    configs = search.load_config()
    if len(configs) == 0:
        print("No configurations set up yet.")
    else:
        for config in configs:
            print(f"Configuration for {config['service']}:")
            print(config['config'])
    display_menu(CONFIG_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(choice, CONFIG_MENU)


MAIN_MENU = {
    "1": ("Show search configurations", display_configs),
}

CONFIG_MENU = {
    "1": ("Add configuration", add_config),
}


def main():
    """Display the main menu and handle user input."""
    display_menu(MAIN_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(choice, MAIN_MENU)


if __name__ == "__main__":
    main()