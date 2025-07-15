"""
Entropy-Playground: GitHub-Native AI Coding Agent Framework

A framework for orchestrating autonomous AI development teams working on GitHub repositories.
"""

__version__ = "0.1.0"
__author__ = "Entropy-Playground Contributors"
__license__ = "MIT"

# Core components
from . import agents
from . import cli
from . import github
from . import infrastructure
from . import logging
from . import runtime

__all__ = [
    "agents",
    "cli", 
    "github",
    "infrastructure",
    "logging",
    "runtime",
]