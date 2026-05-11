"""Git Archaeologist — Git 仓库考古分析工具。"""

__version__ = "0.2.0"

from git_archaeologist.core import GitArchaeologist, RepoSummary
from git_archaeologist.analyzer import Analyzer, AuthorStats, HotspotFile, RepoStats
from git_archaeologist.git_mining import CommitInfo, FileChange, GitMiner

__all__ = [
    "Analyzer",
    "AuthorStats",
    "CommitInfo",
    "FileChange",
    "GitArchaeologist",
    "GitMiner",
    "HotspotFile",
    "RepoStats",
    "RepoSummary",
]
