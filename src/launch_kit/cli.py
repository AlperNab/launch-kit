"""CLI entry point for launch-kit."""
import argparse
import sys
from pathlib import Path
from .generator import LaunchKit


def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete launch marketing package from a GitHub README"
    )
    parser.add_argument("source", help="README file path, GitHub URL, or '-' for stdin")
    parser.add_argument("--repo-name", "-n", help="Repository name (auto-detected if not set)")
    parser.add_argument("--output", "-o", default=".", help="Output directory (default: current dir)")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--print", action="store_true", help="Print to stdout instead of saving file")

    args = parser.parse_args()
    kit = LaunchKit(api_key=args.api_key, model=args.model)

    source = args.source
    if source == "-":
        readme = sys.stdin.read()
        package = kit.from_text(readme, args.repo_name or "my-project")
    elif source.startswith("https://github.com"):
        package = kit.from_github(source)
    else:
        package = kit.from_readme(source)

    if args.print:
        print(f"# {package.repo_name}\n")
        print(f"Tagline: {package.tagline}\n")
        print("## Show HN\n")
        print(package.show_hn)
    else:
        out_path = kit.save(package, args.output)
        print(f"✓ Launch kit saved to: {out_path}")
        print(f"  Tagline: {package.tagline}")
        print(f"  Reddit posts: {list(package.reddit_posts.keys())}")
        print(f"  Twitter thread: {len(package.twitter_thread)} tweets")


if __name__ == "__main__":
    main()
