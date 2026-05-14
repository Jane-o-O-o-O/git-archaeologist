"""Git Archaeologist — Git 仓库考古分析工具。"""

__version__ = "0.8.0"

from git_archaeologist.analyzer import (
    Analyzer,
    AuthorStats,
    BlameEntry,
    BusFactorEntry,
    ChurnEntry,
    CoAuthorPair,
    CommitMessageStats,
    ComplexityPoint,
    ContributorTimelinePoint,
    CouplingPair,
    DirStats,
    FileAgeEntry,
    HealthScore,
    HotspotFile,
    PeriodDiff,
    RepoStats,
    SearchMatch,
    TagEntry,
)
from git_archaeologist.core import GitArchaeologist, RepoSummary
from git_archaeologist.git_mining import CommitInfo, FileChange, GitMiner

__all__ = [
    "Analyzer",
    "AuthorStats",
    "BlameEntry",
    "BusFactorEntry",
    "ChurnEntry",
    "CoAuthorPair",
    "CommitInfo",
    "CommitMessageStats",
    "ComplexityPoint",
    "ContributorTimelinePoint",
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
    "SearchMatch",
    "TagEntry",
]
