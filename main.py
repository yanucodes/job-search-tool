"""Command-line interface for job search."""

import search
import sys
import tracker


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
    configs = search.get_searches()
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


def configure_output_dir():
    """Prompt the user to set the directory where results are saved."""
    current = search.get_output_dir()
    print(f"Current output directory: {current}")
    new_dir = input("Enter a new output directory or press Enter to keep "
                    "current: ")
    if new_dir:
        saved = search.set_output_dir(new_dir)
        print(f"Output directory set to: {saved}")


def display_job(service, record, position, total):
    """Display a job record with its description.

    Args:
        service: Name of the job board the job came from.
        record: Normalized job record.
        position: 1-based position of the job in the review session.
        total: Total number of jobs in the review session.
    """
    print(f"\n--- Job {position}/{total} ({service}) ---")
    print(f"{record['title']}")
    print(f"{record['company']} - {record['location']}")
    print(f"Published: {record['published']}")
    print(f"{record['url']}\n")
    description = search.SERVICES[service].description(record)
    print(description or "No description available.")


def review_jobs():
    """Search for new jobs and review them one by one.

    Each unseen job is displayed with its description, and the user can
    save it to the application list or discard it. Either way the job is
    marked as seen. Quitting leaves the remaining jobs unseen, so they
    come up again in the next review.
    """
    print("Searching...")
    jobs = search.find_new_jobs(tracker.load_seen())
    if not jobs:
        print("No new jobs found.")
        return
    print(f"Found {len(jobs)} new jobs.")
    for i, (service, record) in enumerate(jobs):
        display_job(service, record, i + 1, len(jobs))
        while True:
            choice = input("\n[s]ave to apply later, [d]iscard, [q]uit: ")
            if choice in ("s", "d", "q"):
                break
            print("Invalid choice.")
        if choice == "q":
            return
        tracker.mark_seen(service, record["id"])
        if choice == "s":
            tracker.add_application(service, record)
            print("Saved to application list.")


def go_back():
    """Placeholder for menu navigation. Returns to the previous menu."""
    pass


def exit_program():
    """Exit the application."""
    sys.exit()


MAIN_MENU = {
    "1": ("Search and review new jobs", review_jobs),
    "2": ("Show search configurations", show_config_menu),
    "3": ("Set output directory", configure_output_dir),
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