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

# Anti-scam & fake competition blacklist (immediate rejection)
SCAM_BLACKLIST = [
    "dana kaget", "saldo dana", "giveaway pulsa", "pulsa gratis", "undian berhadiah",
    "tanpa diundi", "transfer pulsa", "slot gacor", "judi online", "pinjol",
    "investasi modal", "arisan online", "tukar kode", "tanpa modal untung jutaan",
    "dm admin minta otp", "bagi bagi iphone gratis", "rekening pribadi tanpa juknis"
]

# Official campus, university & trusted organizer indicators
ORGANIZER_TRUST_KEYWORDS = [
    "universitas", "institut", "politeknik", "kampus", "fakultas", "jurusan",
    "prodi", "bem", "himpunan", "hima", "himatif", "hmif", "ukm", "senat",
    "kemdikbud", "kemendikbud", "puspresnas", "diktiristek", "kementerian",
    "bumn", "telkom", "gdsc", "dicoding", "guidebook", "juknis", "buku panduan",
    "petunjuk teknis", "panitia", "official", "community", "komunitas mahasiswa"
]

def is_legitimate_competition(post: Dict[str, Any]) -> bool:
    """
    Ensures that a competition is legitimate, organized by a credible campus/institution,
    and not a scam, spam, or fake giveaway.
    """
    combined = f"{post.get('title', '')} {post.get('caption', '')}".lower()

    # 1. Immediate rejection if any scam keyword is found
    for scam_word in SCAM_BLACKLIST:
        if scam_word in combined:
            logger.warning(f"Rejected post '{post.get('title')}' due to scam flag: '{scam_word}'")
            return False

    # 2. Check if source is a trusted curated provider or official campus account
    account = post.get("account", "").lower()
    trusted_sources = [
        "info lomba it", "compfest", "arkavidia", "findit", "schematics",
        "hology", "joints", "technofair", "mage", "it_today", "dinamik",
        "lomba_it", "infolombamahasiswa"
    ]
    if any(ts in account for ts in trusted_sources):
        return True

    # 3. For any other source, require at least one verified organizer keyword
    has_trusted_signal = any(okw in combined for okw in ORGANIZER_TRUST_KEYWORDS)
    if not has_trusted_signal:
        logger.warning(f"Rejected post '{post.get('title')}' - missing official campus/organizer signal.")
        return False

    return True

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

def fetch_from_tech_rss(feed_url: str, source_name: str = "Info Lomba IT") -> List[Dict[str, Any]]:
    """Fetches Indonesian campus tech competition posts from dedicated RSS feeds."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser is not installed.")
        return []

    posts = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            post_id = getattr(entry, "id", getattr(entry, "link", None))
            if not post_id:
                continue

            title = getattr(entry, "title", "Info Lomba IT & Hackathon")
            raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

            # Extract high-res poster image URL if available
            image_url = None
            imgs = re.findall(r'<img[^>]+src=[\x22\x27]([^\x22\x27]+)[\x22\x27]', raw_summary)
            if imgs:
                image_url = imgs[0]
            elif hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url")
            elif hasattr(entry, "enclosures") and entry.enclosures:
                image_url = entry.enclosures[0].get("href")

            # Clean HTML tags to form caption
            clean_summary = re.sub(r'<[^>]+>', ' ', raw_summary)
            clean_summary = ' '.join(clean_summary.split()).strip()

            # Collect category tags
            tags = [t.term.lower() for t in getattr(entry, "tags", []) if hasattr(t, "term")]
            combined_text = f"{title} {clean_summary} {' '.join(tags)}"

            posts.append({
                "id": post_id,
                "account": source_name,
                "title": title,
                "caption": clean_summary,
                "url": getattr(entry, "link", ""),
                "image_url": image_url,
                "combined_text": combined_text,
                "published_at": getattr(entry, "published", datetime.utcnow().isoformat())
            })
    except Exception as e:
        logger.error(f"Error fetching tech RSS from {feed_url}: {e}")

    return posts

def fetch_from_rss(feed_url: str, account_name: str) -> List[Dict[str, Any]]:
    """Fetches posts from an RSS/Atom bridge (like RSSHub or RSS.app)."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser is not installed. Run `pip install feedparser` to enable RSS mode.")
        return []

    posts = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            post_id = getattr(entry, "id", entry.link)
            title = getattr(entry, "title", "Postingan Baru")
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            # Clean HTML tags from summary for caption
            clean_caption = re.sub(r"<[^>]+>", " ", summary)
            clean_caption = " ".join(clean_caption.split()).strip()
            
            # Try to find image url from media_content or enclosures
            image_url = None
            imgs = re.findall(r'<img[^>]+src=[\x22\x27]([^\x22\x27]+)[\x22\x27]', summary)
            if imgs:
                image_url = imgs[0]
            elif hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url")
            elif hasattr(entry, "enclosures") and entry.enclosures:
                image_url = entry.enclosures[0].get("href")

            combined_text = f"{title} {clean_caption}"

            posts.append({
                "id": post_id,
                "account": account_name,
                "title": title,
                "caption": clean_caption,
                "url": entry.link,
                "image_url": image_url,
                "combined_text": combined_text,
                "published_at": getattr(entry, "published", datetime.utcnow().isoformat())
            })
    except Exception as e:
        logger.error(f"Error fetching RSS from {feed_url}: {e}")

    return posts

def fetch_from_instaloader(account_name: str, max_posts: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches latest posts using Instaloader.
    NOTE: Instagram strictly rate-limits or blocks anonymous scraping.
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
                "combined_text": caption,
                "published_at": post.date_utc.isoformat() if post.date_utc else datetime.utcnow().isoformat()
            })
            count += 1
    except Exception as e:
        logger.debug(f"Could not fetch from Instagram @{account_name} anonymously: {e}")
    
    return posts

async def check_new_lomba_posts() -> List[Dict[str, Any]]:
    """
    Checks all configured tech RSS feeds and campus Instagram accounts.
    Filters for Indonesian campus tech competitions (Hackathons, UI/UX, CTF, etc.).
    Returns new matching competition posts.
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

    all_fetched_posts = []

    # 2. Fetch from Dedicated Indonesian Campus Tech Feeds
    for feed_url in config.TECH_RSS_FEEDS:
        try:
            feed_posts = await asyncio.to_thread(fetch_from_tech_rss, feed_url, "Info Lomba IT")
            all_fetched_posts.extend(feed_posts)
        except Exception as e:
            logger.error(f"Error checking tech feed {feed_url}: {e}")

    # 3. Fetch from Configured Instagram Accounts (RSS or Instaloader)
    for account in config.TARGET_ACCOUNTS:
        raw_posts = []
        if config.RSS_FEED_TEMPLATE:
            feed_url = config.RSS_FEED_TEMPLATE.format(username=account)
            raw_posts = await asyncio.to_thread(fetch_from_rss, feed_url, account)
        elif config.IG_USERNAME and config.IG_PASSWORD:
            raw_posts = await asyncio.to_thread(fetch_from_instaloader, account, 3)
        all_fetched_posts.extend(raw_posts)

    is_initial_seeding = database.get_total_posts_count() == 0
    matched_candidates = []

    for post in all_fetched_posts:
        if database.is_post_seen(post["id"]):
            continue

        # Filter out scam / fake competitions
        if not is_legitimate_competition(post):
            continue

        text_to_check = post.get("combined_text") or f"{post.get('title', '')} {post.get('caption', '')}"
        matches = check_keywords(text_to_check)
        if matches:
            post["matched_keywords"] = matches
            matched_candidates.append(post)

    if not matched_candidates:
        return []

    # If first time running (empty DB), silently seed all existing posts so bot does NOT spam or ping on update/startup
    if is_initial_seeding:
        logger.info(f"Initial run/update: Silently seeding {len(matched_candidates)} existing posts into database. No notifications or pings sent.")
        for post in matched_candidates:
            database.mark_post_seen(
                post_id=post["id"],
                account=post.get("account", "Instagram Kampus"),
                url=post["url"],
                title=post.get("title", "Lomba Kampus")
            )
        # Return empty list: SILENT on startup/updates!
        return []

    # Normal cycle: mark seen and return all new items
    for post in matched_candidates:
        database.mark_post_seen(
            post_id=post["id"],
            account=post.get("account", "Info Lomba IT"),
            url=post["url"],
            title=post.get("title", "Info Lomba IT & Hackathon")
        )
        new_competitions.append(post)

    return new_competitions

