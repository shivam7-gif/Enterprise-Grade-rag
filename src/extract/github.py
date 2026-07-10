import requests
import json
import os
import logging
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class Repo(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    url: HttpUrl = Field(alias="html_url")
    default_branch: Optional[str] = None
    language: Optional[str] = None
    stars: int = Field(alias="stargazers_count", default=0)
    forks: int = Field(alias="forks_count", default=0)
    topics: list[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True, 
        "extra": "ignore",        
    }


class GitHubConnector:
    def __init__(self, org="kubeflow", output_dir="../data/raw"):
        self.org = org
        self.url = f"https://api.github.com/orgs/{org}/repos"
        self.params = {"per_page": 100, "page": 1}
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json"})

    def fetch_repositories(self) -> list[dict]:
        """Fetching raw repo data from GitHub."""
        logger.info(f"Fetching repos for org: {self.org}")
        resp = self.session.get(self.url, params=self.params)
        resp.raise_for_status()
        return resp.json()

    def parse_repos(self, raw_repos: list[dict]) -> list[Repo]:
        """Validate + parse raw dicts into Repo models, skipping bad records."""
        parsed = []
        for raw in raw_repos:
            try:
                parsed.append(Repo.model_validate(raw))
            except ValidationError as e:
                logger.warning(f"Skipping repo due to validation error: {e}")
        return parsed

    def save_json(self, repos: list[Repo], filename="repos.json"):
        """Save validated Repo models as a JSON file."""
        output_path = os.path.join(self.output_dir, filename)
        data = [repo.model_dump(mode="json") for repo in repos]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(data)} repos to {output_path}")
        return output_path

    def run(self) -> list[Repo]:
        raw_repos = self.fetch_repositories()
        repos = self.parse_repos(raw_repos)
        self.save_json(repos)
        print(len(repos))
        return repos


if __name__ == "__main__":
    connector = GitHubConnector(org="kubeflow", output_dir="../data/raw")
    repos = connector.run()
    print(json.dumps([r.model_dump(mode="json") for r in repos[:2]], indent=2))