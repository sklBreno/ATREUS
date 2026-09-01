"""Integration tests for the ATREUS foundation Bootstrap."""

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader


def test_bootstrap_runs_configuration_foundation_flow() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "false"},
    )
    manager = ConfigurationManager(loader=loader)

    configuration = Bootstrap(configuration_provider=manager).run()

    assert isinstance(configuration, Configuration)
    assert configuration.debug is False
