"""Command-line interface to configure the job search.

Searching and reviewing jobs happens in the web interface (app.py).
"""

import search
import sys


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
    configs = search.get_searches()
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
    return select_number("Select a configuration by number: ",
                         len(search.get_searches()))


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


def configure_output_dir():
    """Prompt the user to set the directory where results are saved."""
    current = search.get_output_dir()
    print(f"Current output directory: {current}")
    new_dir = input("Enter a new output directory or press Enter to keep "
                    "current: ")
    if new_dir:
        saved = search.set_output_dir(new_dir)
        print(f"Output directory set to: {saved}")


def select_number(prompt, count):
    """Prompt the user to pick a number between 1 and count.

    Args:
        prompt: Text to show when asking for input.
        count: Highest valid number.

    Returns:
        0-based index of the selection, or None if the user cancels.
    """
    print("0. Cancel")
    while True:
        choice = input(prompt)
        if choice.isdigit():
            choice = int(choice)
            if not choice:
                return None
            elif 0 < choice <= count:
                return choice - 1
        print("Invalid choice.")


def go_back():
    """Placeholder for menu navigation. Returns to the previous menu."""
    pass


def exit_program():
    """Exit the application."""
    sys.exit()


MAIN_MENU = {
    "1": ("Show search configurations", show_config_menu),
    "2": ("Set output directory", configure_output_dir),
    "0": ("Exit", exit_program),
}

CONFIG_MENU = {
    "1": ("Add configuration", add_config),
    "2": ("Update configuration", update_config),
    "3": ("Remove configuration", remove_config),
    "0": ("Back", go_back),
}


def main():
    """Display the main menu in a loop until the user exits."""
    while True:
        display_menu(MAIN_MENU)
        choice = input("Enter your choice: ")
        handle_menu_choice(choice, MAIN_MENU)


if __name__ == "__main__":
    main()