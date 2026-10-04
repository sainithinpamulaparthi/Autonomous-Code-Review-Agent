import os
from dataclasses import dataclass

try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    github_token: str = ""
    github_webhook_secret: str = ""
    sonar_url: str = "http://localhost:9000"
    sonar_token: str = ""
    sonar_project_key: str = ""
    llm_provider: str = "ollama"
    llm_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    llm_timeout: int = 60
    llm_max_issues: int = 8
    max_files: int = 25
    max_file_bytes: int = 200_000

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ.get
        return cls(
            github_token=e("GITHUB_TOKEN", ""),
            github_webhook_secret=e("GITHUB_WEBHOOK_SECRET", ""),
            sonar_url=e("SONAR_URL", "http://localhost:9000").rstrip("/"),
            sonar_token=e("SONAR_TOKEN", ""),
            sonar_project_key=e("SONAR_PROJECT_KEY", ""),
            llm_provider=e("LLM_PROVIDER", "ollama").strip().lower(),
            llm_model=e("LLM_MODEL", ""),
            ollama_base_url=e("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            openai_api_key=e("OPENAI_API_KEY", ""),
            llm_timeout=_int("LLM_TIMEOUT", 60),
            llm_max_issues=_int("LLM_MAX_ISSUES", 8),
            max_files=_int("MAX_FILES", 25),
            max_file_bytes=_int("MAX_FILE_BYTES", 200_000),
        )

    @property
    def model_name(self) -> str:
        if self.llm_model:
            return self.llm_model
        return "gpt-4o-mini" if self.llm_provider == "openai" else "llama3.1"

    @property
    def sonar_configured(self) -> bool:
        return bool(self.sonar_token and self.sonar_project_key)
