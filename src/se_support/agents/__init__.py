"""Agent scaffolds.

An :class:`AgentRunner` produces a patch for a task inside a workspace. The mock
agent (deterministic, no LLM) validates the whole pipeline; real adapters
(mini-SWE-agent, Agentless) implement the same interface later.
"""

from se_support.agents.base import AgentRunner
from se_support.agents.chat_client import (
    ChatClient,
    OpenAIChatClient,
    ScriptedChatClient,
)
from se_support.agents.llm_agent import LLMAgent
from se_support.agents.mock_agent import MockAgent

__all__ = [
    "AgentRunner",
    "MockAgent",
    "LLMAgent",
    "ChatClient",
    "OpenAIChatClient",
    "ScriptedChatClient",
]
