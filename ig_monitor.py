import logging
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import config
import database

logger = logging.getLogger(__name__)

# Fallback / Demo Mock items for testing the bot easily
SAMPLE_MOCK_POSTS = [
    {
        "id": "mock_hackathon_001",
        "account": "hackathon_id",
        "title": "National Tech Hackathon 2026 - Innovation for AI & Cloud",
        "caption": (
            "🔥 REGISTRASI TELAH DIBUKA! 🔥\n\n"
            "Tunjukkan solusi inovatifmu di National Tech Hackathon 2026! "
            "Kategori: Web & Mobile App, AI Solutions, Cybersecurity.\n\n"
            "🏆 Total Hadiah: Rp 75.000.000 + Beasiswa & Sertifikat Nasional\n"
            "📅 Deadline Pendaftaran: 30 November 2026\n"
            "📍 Lokasi: Hybrid (Online & Final di Jakarta)\n\n"
            "Bentuk timmu (1-3 orang) dan daftarkan segera sekarang juga! Link di bio @hackathon_id."
        ),
        "url": "https://www.instagram.com/p/mock_hackathon_001/",
        "image_url": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800",
        "published_at": datetime.utcnow().isoformat(),
    },
    {
        "id": "mock_hackathon_002",
        "account": "infolomba",
        "title": "Lomba Competitive Programming & UI/UX Design Competition",
        "caption": (
            "🚀 CALL FOR PARTICIPANTS: Compfest IT Challenge 2026 🚀\n\n"
            "Halo Hunters Lomba! Pendaftaran cabang lomba Competitive Programming dan "
            "UI/UX Design resmi dibuka untuk seluruh mahasiswa & siswa se-Indonesia!\n\n"
            "✨ Benefits:\n- E-Certificate\n- Mentoring Session\n- Total Hadiah Rp 35.000.000\n\n"
            "Yuk asah kemampuan coding dan design kamu! Cek link pendaftaran di bio."
        ),
        "url": "https://www.instagram.com/p/mock_hackathon_002/",
        "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800",
        "published_at": datetime.utcnow().isoformat(),
    }
]

def check_keywords(text: str) -> List[str]:
    """Finds which target keywords match the text."""
    if not config.ENABLE_KEYWORD_FILTER:
        return ["keyword-filter-disabled"]
    
    text_lower = text.lower()
    matches = []
    for kw in config.KEYWORDS:
        if kw in text_lower:
            matches.append(kw)
    return matches

def fetch_from_rss(feed_url: str, account_name: str) -> List[Dict[str, Any]]:
    """Fetches posts from an RSS/Atom bridge (like RSSHub or RSS.app)."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser is not installed. Run `pip install feedparser` to enable RSS mode.")
        return []

    feed = feedparser.parse(feed_url)
    posts = []
    for entry in feed.entries:
        post_id = getattr(entry, "id", entry.link)
        title = getattr(entry, "title", "Postingan Baru")
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        # Clean HTML tags from summary for caption
        clean_caption = re.sub(r"<[^>]+>", "", summary).strip()
        
        # Try to find image url from media_content or enclosures
        image_url = None
        if hasattr(entry, "media_content") and entry.media_content:
            image_url = entry.media_content[0].get("url")
        elif hasattr(entry, "enclosures") and entry.enclosures:
            image_url = entry.enclosures[0].get("href")

        posts.append({
            "id": post_id,
            "account": account_name,
            "title": title,
            "caption": clean_caption,
            "url": entry.link,
            "image_url": image_url,
            "published_at": getattr(entry, "published", datetime.utcnow().isoformat())
        })
    return posts

def fetch_from_instaloader(account_name: str, max_posts: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches latest posts using Instaloader.
    NOTE: Instagram strictly rate-limits or blocks anonymous scraping.
    If you experience issues, consider logging in via IG_USERNAME/IG_PASSWORD or using RSSHub.
    """
    try:
        import instaloader
    except ImportError:
        logger.warning("instaloader is not installed. Run `pip install instaloader`.")
        return []

    posts = []
    try:
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
            quiet=True
        )

        if config.IG_USERNAME and config.IG_PASSWORD:
            try:
                L.login(config.IG_USERNAME, config.IG_PASSWORD)
                logger.info(f"Successfully logged into Instagram as {config.IG_USERNAME}")
            except Exception as login_err:
                logger.error(f"Failed to log in to Instagram: {login_err}")

        profile = instaloader.Profile.from_username(L.context, account_name)
        count = 0
        for post in profile.get_posts():
            if count >= max_posts:
                break
            
            caption = post.caption or ""
            posts.append({
                "id": post.shortcode,
                "account": account_name,
                "title": f"Postingan @{account_name}",
                "caption": caption,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "image_url": post.url,
                "published_at": post.date_utc.isoformat() if post.date_utc else datetime.utcnow().isoformat()
            })
            count += 1
    except Exception as e:
        logger.error(f"Error fetching from Instagram @{account_name} via Instaloader: {e}")
    
    return posts

async def check_new_lomba_posts() -> List[Dict[str, Any]]:
    """
    Checks all configured accounts for new competition/hackathon posts.
    Returns only posts that match keywords and have not been seen before.
    """
    new_competitions = []

    # 1. If mock data is enabled, test with mock posts
    if config.ENABLE_MOCK_DATA:
        for post in SAMPLE_MOCK_POSTS:
            if not database.is_post_seen(post["id"]):
                matches = check_keywords(post["caption"])
                if matches:
                    post["matched_keywords"] = matches
                    database.mark_post_seen(
                        post_id=post["id"],
                        account=post["account"],
                        url=post["url"],
                        title=post["title"]
                    )
                    new_competitions.append(post)
        return new_competitions

    # 2. Iterate through configured accounts
    for account in config.TARGET_ACCOUNTS:
        raw_posts = []

        # Check RSS template if configured
        if config.RSS_FEED_TEMPLATE:
            feed_url = config.RSS_FEED_TEMPLATE.format(username=account)
            # Run blocking network call in thread executor
            raw_posts = await asyncio.to_thread(fetch_from_rss, feed_url, account)
        else:
            # Fallback to Instaloader
            raw_posts = await asyncio.to_thread(fetch_from_instaloader, account, 5)

        for post in raw_posts:
            # Check if already processed
            if database.is_post_seen(post["id"]):
                continue

            # Check keyword relevance
            matches = check_keywords(post["caption"])
            if matches:
                post["matched_keywords"] = matches
                # Mark as seen
                database.mark_post_seen(
                    post_id=post["id"],
                    account=post["account"],
                    url=post["url"],
                    title=post.get("title", f"Lomba Baru dari @{account}")
                )
                new_competitions.append(post)

    return new_competitions

