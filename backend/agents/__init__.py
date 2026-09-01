"""Auteur agents package — Director, Research, Consistency.

Exactly three agents (justify every agent; agent count is not
a quality metric). One orchestrator (Director) + two specialists (Research,
Consistency). They share a Cloud Run process and communicate via in-memory ADK
calls (no network hop between them).
"""
