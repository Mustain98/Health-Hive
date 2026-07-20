"""LLM agents.

One package per agent. Each owns its own prompts, tools, response schemas and
middleware — nothing is shared between agents. The only common dependencies are
`app.core.llm` (how to reach a model) and the canonical domain schemas.
"""
