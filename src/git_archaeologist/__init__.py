"""Git Archaeologist — Git 仓库考古分析工具。"""

__version__ = "0.6.0"

from git_archaeologist.analyzer import (
    Analyzer,
    AuthorStats,
    BlameEntry,
    BusFactorEntry,
    ChurnEntry,
    CommitMessageStats,
    ComplexityPoint,
    CouplingPair,
    DirStats,
    FileAgeEntry,
    HealthScore,
    HotspotFile,
    PeriodDiff,
    RepoStats,
)
from git_archaeologist.core import GitArchaeologist, RepoSummary
from git_archaeologist.git_mining import CommitInfo, FileChange, GitMiner

__all__ = [
    "Analyzer",
    "AuthorStats",
    "BlameEntry",
    "BusFactorEntry",
    "ChurnEntry",
    "CommitInfo",
    "CommitMessageStats",
    "ComplexityPoint",
    "CouplingPair",
    "DirStats",
    "FileAgeEntry",
    "FileChange",
    "GitArchaeologist",
    "GitMiner",
    "HealthScore",
    "HotspotFile",
    "PeriodDiff",
    "RepoStats",
    "RepoSummary",
]
