#!/usr/bin/env python3
"""
Pulls live data and rewrites the marked sections of README.md.
Runs on a schedule via GitHub Actions — see .github/workflows/update-readme.yml

Sections it touches (must exist in README.md as HTML comment pairs):
  <!--BLOG:START--> ... <!--BLOG:END-->
  <!--LEETCODE:START--> ... <!--LEETCODE:END-->
  <!--COMMITS:START--> ... <!--COMMITS:END-->
"""

import os
import re
import sys
import requests
import feedparser

GITHUB_USERNAME = "aryaprakashraj"
LEETCODE_USERNAME = "aryaprakashraj"
README_PATH = "README.md"

# Candidate feed URLs to try for arya.dev — confirm which one is real
# and delete the others once you know.
BLOG_FEED_CANDIDATES = [
    "https://aryaprakashraj.vercel.app/rss.xml",
    "https://aryaprakashraj.vercel.app/feed.xml",
    "https://aryaprakashraj.vercel.app/rss",
    "https://aryaprakashraj.vercel.app/feed",
]


def get_latest_blog_post():
    for url in BLOG_FEED_CANDIDATES:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                entry = feed.entries[0]
                title = entry.get("title", "Untitled")
                link = entry.get("link", "https://aryaprakashraj.vercel.app")
                return f"$ curl arya.dev/latest\n> [{title}]({link})"
        except Exception:
            continue
    return "$ curl arya.dev/latest\n> (feed not wired up yet — check BLOG_FEED_CANDIDATES in update_readme.py)"


def get_leetcode_stats():
    try:
        r = requests.get(
            f"https://leetcode-stats-api.herokuapp.com/{LEETCODE_USERNAME}",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        total = data.get("totalSolved", "?")
        easy = data.get("easySolved", "?")
        medium = data.get("mediumSolved", "?")
        hard = data.get("hardSolved", "?")
        ranking = data.get("ranking", "?")
        return (
            f"$ leetcode --stats\n"
            f"> Solved: {total}  (Easy {easy} · Medium {medium} · Hard {hard})\n"
            f"> Global rank: {ranking}"
        )
    except Exception as e:
        return f"$ leetcode --stats\n> (unavailable right now: {e})"


def get_recent_commits():
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Authorization": f"token {token}"} if token else {}
    try:
        r = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}/events/public",
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        events = r.json()
        lines = []
        for event in events:
            if event.get("type") == "PushEvent":
                repo = event["repo"]["name"].split("/")[-1]
                for commit in event["payload"].get("commits", []):
                    msg = commit["message"].splitlines()[0][:60]
                    sha = commit["sha"][:7]
                    lines.append(f"{sha} ({repo}) {msg}")
            if len(lines) >= 3:
                break
        if not lines:
            return "$ git log --oneline -3\n> (no recent public pushes)"
        formatted = "\n".join(f"> {line}" for line in lines[:3])
        return f"$ git log --oneline -3\n{formatted}"
    except Exception as e:
        return f"$ git log --oneline -3\n> (unavailable right now: {e})"


def replace_section(content, tag, new_text):
    pattern = re.compile(
        rf"(<!--{tag}:START-->)(.*?)(<!--{tag}:END-->)", re.DOTALL
    )
    replacement = f"\\1\n```\n{new_text}\n```\n\\3"
    if not pattern.search(content):
        print(f"WARNING: marker pair for {tag} not found in {README_PATH}")
        return content
    return pattern.sub(replacement, content)


def main():
    if not os.path.exists(README_PATH):
        print(f"ERROR: {README_PATH} not found in repo root.")
        sys.exit(1)

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_section(content, "BLOG", get_latest_blog_post())
    content = replace_section(content, "LEETCODE", get_leetcode_stats())
    content = replace_section(content, "COMMITS", get_recent_commits())

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("README.md updated.")


if __name__ == "__main__":
    main()
