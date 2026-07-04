from atreus.configuration.configuration import Configuration


class Bootstrap:

    def run(self) -> None:

        configuration = Configuration()

        print("=" * 50)
        print(configuration.app_name)
        print("Personal Intelligence Platform")
        print(f"Version: {configuration.version}")
        print("Status: Initializing...")
        print("=" * 50)

        print("Loading configuration...")

        print("Initialization complete!")
