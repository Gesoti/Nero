"""
Blog post loader. Reads markdown files with YAML frontmatter from app/blog/posts/.

Each .md file must have a YAML frontmatter block:
---
title: "Post Title"
slug: "post-slug"
date: "2026-02-26"
description: "Meta description for SEO"
author: "Nero Team"
---

Markdown content here...
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import mistune
import yaml

logger = logging.getLogger(__name__)

POSTS_DIR = Path(__file__).parent / "blog" / "posts"


@dataclass(frozen=True)
class BlogPost:
    title: str
    slug: str
    date: date
    description: str
    author: str
    content_html: str


_markdown = mistune.create_markdown(escape=False)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split YAML frontmatter from markdown content."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return meta, body


def load_post(slug: str) -> BlogPost | None:
    """Load a single blog post by slug."""
    filepath = POSTS_DIR / f"{slug}.md"
    if not filepath.is_file():
        return None
    return _load_file(filepath)


def load_all_posts() -> list[BlogPost]:
    """Load all blog posts, sorted by date descending (newest first)."""
    if not POSTS_DIR.is_dir():
        return []
    posts: list[BlogPost] = []
    for filepath in POSTS_DIR.glob("*.md"):
        post = _load_file(filepath)
        if post:
            posts.append(post)
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def _load_file(filepath: Path) -> BlogPost | None:
    """Parse a single markdown file into a BlogPost."""
    try:
        raw = filepath.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        if not meta.get("title") or not meta.get("slug"):
            logger.warning("Blog post %s missing title or slug, skipping", filepath)
            return None
        post_date = meta.get("date", date.today())
        if isinstance(post_date, str):
            post_date = date.fromisoformat(post_date)
        return BlogPost(
            title=meta["title"],
            slug=meta["slug"],
            date=post_date,
            description=meta.get("description", ""),
            author=meta.get("author", "Nero Team"),
            content_html=_markdown(body),
        )
    except Exception:
        logger.exception("Failed to load blog post %s", filepath)
        return None
