# core/profiles/__init__.py

from core.profiles.identity import IdentityManager
from core.profiles.knowledge_graph import KnowledgeGraph
from core.profiles.profile_engine import ProfileEngine

__all__ = ["IdentityManager", "KnowledgeGraph", "ProfileEngine"]
