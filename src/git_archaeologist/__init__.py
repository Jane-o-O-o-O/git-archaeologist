"""Git Archaeologist — Git 仓库考古分析工具。"""

__version__ = "0.5.0"

from git_archaeologist.analyzer import (
    Analyzer,
    AuthorStats,
    BusFactorEntry,
    ChurnEntry,
    CommitMessageStats,
    CouplingPair,
    DirStats,
    FileAgeEntry,
    HealthScore,
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
    "CommitMessageStats",
    "CouplingPair",
    "DirStats",
    "FileAgeEntry",
    "FileChange",
    "GitArchaeologist",
    "GitMiner",
    "HealthScore",
    "HotspotFile",
    "RepoStats",
    "RepoSummary",
]
