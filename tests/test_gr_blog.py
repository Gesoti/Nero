"""Tests for Greek blog posts and content."""
import pytest

from app.blog import load_all_posts


def test_gr_blog_posts_exist() -> None:
    """At least 3 blog posts with country: gr must exist."""
    posts = load_all_posts()
    gr_posts = [p for p in posts if p.country == "gr"]
    assert len(gr_posts) >= 3, f"Expected 3+ gr posts, found {len(gr_posts)}"


def test_gr_blog_post_word_count() -> None:
    """Each gr blog post must be 800+ words."""
    posts = load_all_posts()
    gr_posts = [p for p in posts if p.country == "gr"]
    for post in gr_posts:
        # Count words in the HTML content
        word_count = len(post.content_html.split())
        assert (
            word_count >= 800
        ), f"Post '{post.title}' has {word_count} words, need 800+"


def test_gr_blog_post_titles() -> None:
    """Greek blog posts should have specific titles."""
    posts = load_all_posts()
    gr_posts = {p.slug: p for p in posts if p.country == "gr"}

    expected_slugs = {
        "athens-water-supply-system",
        "mornos-reservoir-athens-lifeline",
        "marathon-dam-history",
    }

    found_slugs = set(gr_posts.keys())
    assert (
        expected_slugs.issubset(found_slugs)
    ), f"Missing expected blog posts. Expected: {expected_slugs}, Found: {found_slugs}"
