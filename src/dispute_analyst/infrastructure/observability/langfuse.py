"""Tracing in Langfuse through LangChain callbacks: every model and tool call of an analysis.

The agents know only LangChain's BaseCallbackHandler; bootstrap plugs Langfuse in.
"""

from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler


def langfuse_callback(public_key: str, secret_key: str, base_url: str) -> BaseCallbackHandler:
    """Register the Langfuse client for these keys and return a handler that reports to it.

    Traces go out in the background and are flushed when the process exits. If Langfuse is
    down, the SDK logs the error and the analysis carries on.
    """
    Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    return CallbackHandler(public_key=public_key)
