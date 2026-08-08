"""Plugin subsystem."""

from local_agent.plugins.lifecycle import PluginLifecycle
from local_agent.plugins.supervisor import PluginSupervisor

__all__ = ["PluginSupervisor", "PluginLifecycle"]
