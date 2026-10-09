"""Langfuse observability integration for LLM and embedding trace exploration.

Uses the native Langfuse SDK, which configures OpenTelemetry export
automatically.  LLM/embedding spans are captured via OpenInference LangChain
auto-instrumentation.  Designed to be fully optional: when Langfuse is disabled
or misconfigured the rest of the application is unaffected.
"""
