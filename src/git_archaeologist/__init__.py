"""Git Archaeologist — Git 仓库考古分析工具。"""

__version__ = "0.4.0"

from git_archaeologist.analyzer import (
    Analyzer,
    AuthorStats,
    BusFactorEntry,
    ChurnEntry,
    CouplingPair,
    DirStats,
    FileAgeEntry,
    HotspotFile,
    RepoStats,
)
from git_archaeologist.core import GitArchaeologist, RepoSummary
from git_archaeologist.git_mining import CommitInfo, FileChange, GitMiner

__all__ = [
    "Analyzer",
    "AuthorStats",
    "BusFactorEntry",
    "ChurnEntry",
    "CommitInfo",
    "CouplingPair",
    "DirStats",
    "FileAgeEntry",
    "FileChange",
    "GitArchaeologist",
    "GitMiner",
    "HotspotFile",
    "RepoStats",
    "RepoSummary",
]
