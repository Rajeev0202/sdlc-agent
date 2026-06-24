"""Core domain package: data contracts, pipeline orchestrator, and app config.

Submodules are imported explicitly (e.g. ``from sdlc_agent.core.models import
StoryBacklog``) rather than re-exported here, to avoid import cycles with the
stage and skill modules that depend on the contracts in ``models``.
"""
