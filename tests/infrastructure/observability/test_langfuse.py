from langchain_core.callbacks import BaseCallbackHandler

from dispute_analyst.infrastructure.observability.langfuse import langfuse_callback


def test_returns_a_langchain_callback() -> None:
    # Only builds the client: nothing is sent until a traced call happens.
    handler = langfuse_callback("pk-lf-test", "sk-lf-test", "http://localhost:3000")

    assert isinstance(handler, BaseCallbackHandler)
