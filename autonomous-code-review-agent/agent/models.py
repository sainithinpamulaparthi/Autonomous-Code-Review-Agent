from typing import List

from pydantic import BaseModel, Field


class Issue(BaseModel):
    file: str
    line: int = 0
    severity: str = "MINOR"      # CRITICAL | MAJOR | MINOR | INFO
    category: str = "quality"    # security | bug | quality | performance
    rule: str
    message: str
    source: str = "builtin"      # builtin | sonarqube | sonarqube (simulated)
    explanation: str = ""
    suggested_fix: str = ""
    snippet: str = ""
    ai_generated: bool = False   # True when explanation/fix came from the LLM


class Report(BaseModel):
    target: str
    mode: str                    # paste | github-repo | github-pr | demo | local
    simulated: bool = False      # True only in Demo Mode
    created: str = ""
    files_reviewed: int = 0
    issues: List[Issue] = Field(default_factory=list)
    score: int = 100
    verdict: str = ""
    summary: str = ""
    llm_used: bool = False
    notes: List[str] = Field(default_factory=list)
