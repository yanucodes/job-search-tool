import search


def display_menu(menu):
    for i, menu_item in enumerate(menu):
        print(f"{i}. {menu_item[0]}")


def handle_menu_choice(index, menu):
    menu[index][1]()


def add_config():
    print("Available search services:")
    for service in search.SERVICES:
        print(service)
    service = input("Which service would you like to use? ")
    search.add_config(service)


def display_configs():
    configs = search.load_config()
    if len(configs) == 0:
        print("No configurations set up yet.")
    else:
        for config in configs:
            print(f"Configuration for {config['service']}:")
            print(config['config'])
    display_menu(CONFIG_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(int(choice), CONFIG_MENU)


MAIN_MENU = (
    ('Show search configurations', display_configs),
)

CONFIG_MENU = (
    ('Add configuration', add_config),
)


def main():
    display_menu(MAIN_MENU)
    choice = input("Enter your choice: ")
    handle_menu_choice(int(choice), MAIN_MENU)


if __name__ == "__main__":
    main()