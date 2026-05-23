"""LaunchKit — reads a GitHub README and generates a complete launch package."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import anthropic


@dataclass
class LaunchPackage:
    repo_name: str
    tagline: str
    show_hn: str
    product_hunt_tagline: str
    product_hunt_description: str
    reddit_posts: dict[str, str]     # subreddit → post text
    twitter_thread: list[str]         # list of tweets
    linkedin_post: str
    devto_intro: str
    keywords: list[str]


SYSTEM = """You are an expert at launching open-source developer tools.
You write launch copy that is honest, specific, and gets developers excited.
Never use buzzwords. Always lead with what the tool actually does.
Reply ONLY with valid JSON — no markdown fences, no explanation."""

PROMPT = """
Here is a GitHub README for an open-source project:

---
{readme}
---

Generate a complete launch marketing package as JSON with these exact keys:

{{
  "tagline": "One sentence. What it does. Under 12 words.",
  "show_hn": "Full Hacker News 'Show HN:' post. 200-400 words. Technical, honest, no hype. Start with: Show HN: [project name] – [tagline]",
  "product_hunt_tagline": "Under 60 chars. Punchy. Action-oriented.",
  "product_hunt_description": "3 paragraphs. Problem → solution → why open source. 150-200 words total.",
  "reddit_posts": {{
    "r/programming": "post text",
    "r/webdev": "post text",
    "r/SideProject": "post text",
    "r/MachineLearning": "post text or null if not relevant",
    "r/LocalLLaMA": "post text or null if not relevant"
  }},
  "twitter_thread": [
    "Tweet 1 — hook + what it is",
    "Tweet 2 — the problem it solves",
    "Tweet 3 — how it works (technical)",
    "Tweet 4 — key feature or demo",
    "Tweet 5 — CTA with GitHub link"
  ],
  "linkedin_post": "Professional tone. 150 words. Story arc: problem → what I built → why open source → link.",
  "devto_intro": "First 2 paragraphs of a dev.to article. Hook developers. End with a teaser for the technical deep-dive.",
  "keywords": ["5", "to", "10", "SEO", "keywords"]
}}
"""


class LaunchKit:
    """Generate a complete launch marketing package from a GitHub README."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def from_readme(self, readme_path: str | Path) -> LaunchPackage:
        """Generate launch package from a local README file."""
        readme = Path(readme_path).read_text(encoding="utf-8")
        return self._generate(readme, Path(readme_path).parent.name)

    def from_github(self, github_url: str) -> LaunchPackage:
        """Generate launch package from a GitHub repo URL."""
        import urllib.request
        # Convert github.com URL to raw README
        url = github_url.rstrip("/")
        if "raw.githubusercontent.com" not in url:
            # e.g. https://github.com/user/repo → raw README
            parts = url.replace("https://github.com/", "").split("/")
            owner, repo = parts[0], parts[1]
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
        else:
            raw_url = url

        with urllib.request.urlopen(raw_url) as resp:
            readme = resp.read().decode("utf-8")

        repo_name = github_url.rstrip("/").split("/")[-1]
        return self._generate(readme, repo_name)

    def from_text(self, readme_text: str, repo_name: str = "my-project") -> LaunchPackage:
        """Generate launch package from README text."""
        return self._generate(readme_text, repo_name)

    def _generate(self, readme: str, repo_name: str) -> LaunchPackage:
        # Truncate very long READMEs to avoid token limits
        if len(readme) > 12000:
            readme = readme[:12000] + "\n\n[README truncated for brevity]"

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=SYSTEM,
            messages=[{"role": "user", "content": PROMPT.format(readme=readme)}],
        )

        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            data = json.loads(match.group()) if match else {}

        reddit = data.get("reddit_posts", {})
        # Remove null reddit posts
        reddit = {k: v for k, v in reddit.items() if v}

        return LaunchPackage(
            repo_name=repo_name,
            tagline=data.get("tagline", ""),
            show_hn=data.get("show_hn", ""),
            product_hunt_tagline=data.get("product_hunt_tagline", ""),
            product_hunt_description=data.get("product_hunt_description", ""),
            reddit_posts=reddit,
            twitter_thread=data.get("twitter_thread", []),
            linkedin_post=data.get("linkedin_post", ""),
            devto_intro=data.get("devto_intro", ""),
            keywords=data.get("keywords", []),
        )

    def save(self, package: LaunchPackage, output_dir: str | Path = ".") -> Path:
        """Save the launch package to a markdown file."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{package.repo_name}-launch-kit.md"

        lines = [
            f"# Launch Kit — {package.repo_name}",
            "",
            f"**Tagline:** {package.tagline}",
            "",
            "---",
            "",
            "## Hacker News — Show HN",
            "",
            package.show_hn,
            "",
            "---",
            "",
            "## Product Hunt",
            "",
            f"**Tagline:** {package.product_hunt_tagline}",
            "",
            package.product_hunt_description,
            "",
            "---",
            "",
            "## Reddit Posts",
            "",
        ]

        for sub, text in package.reddit_posts.items():
            lines += [f"### {sub}", "", text, ""]

        lines += [
            "---",
            "",
            "## Twitter / X Thread",
            "",
        ]
        for i, tweet in enumerate(package.twitter_thread, 1):
            lines += [f"**{i}/{len(package.twitter_thread)}** {tweet}", ""]

        lines += [
            "---",
            "",
            "## LinkedIn",
            "",
            package.linkedin_post,
            "",
            "---",
            "",
            "## Dev.to Intro",
            "",
            package.devto_intro,
            "",
            "---",
            "",
            f"**Keywords:** {', '.join(package.keywords)}",
        ]

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
