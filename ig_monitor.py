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
        "account": "@compfest",
        "title": "COMPFEST 16 - National Tech Hackathon & Innovation Challenge",
        "caption": (
            "🔥 REGISTRASI TELAH DIBUKA! 🔥\n\n"
            "Tunjukkan solusi inovatifmu di COMPFEST Hackathon!\n"
            "Kategori: Web & Mobile App, AI Solutions, Cybersecurity.\n\n"
            "🏆 Total Hadiah: Rp 75.000.000 + Beasiswa & Sertifikat Nasional\n"
            "📅 Deadline Pendaftaran: 30 November 2026\n"
            "📍 Penyelenggara: Fakultas Ilmu Komputer Universitas Indonesia (@compfest)\n\n"
            "Bentuk timmu dan daftarkan segera sekarang juga! Link di bio @compfest."
        ),
        "url": "https://www.instagram.com/p/DdECA40pnMK/",
        "image_url": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800",
        "published_at": datetime.utcnow().isoformat(),
    },
    {
        "id": "mock_hackathon_002",
        "account": "@infolomba",
        "title": "Lomba Competitive Programming & UI/UX Design Competition",
        "caption": (
            "🚀 CALL FOR PARTICIPANTS: Compfest IT Challenge 2026 🚀\n\n"
            "Halo Hunters Lomba! Pendaftaran cabang lomba Competitive Programming dan "
            "UI/UX Design resmi dibuka untuk seluruh mahasiswa & siswa se-Indonesia!\n\n"
            "✨ Benefits:\n- E-Certificate\n- Mentoring Session\n- Total Hadiah Rp 35.000.000\n\n"
            "Yuk asah kemampuan coding dan design kamu! Cek link pendaftaran di bio."
        ),
        "url": "https://www.instagram.com/p/DdLCkIrE9s9/",
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

SPONSOR_FILTER = {'dewaweb', 'gmail.com', 'yahoo.com', 'telkom', 'bca', 'dana', 'unj.ac.id', 'ac.id', 'sch.id'}

def extract_instagram_details(title: str, raw_desc: str, fallback_link: str) -> tuple[str, str]:
    """
    Extracts authentic campus organizer Instagram handle and direct Instagram URL.
    Guarantees that no external blog link (such as infolombait.com) is used.
    """
    import html
    from bs4 import BeautifulSoup

    text = BeautifulSoup(raw_desc, 'html.parser').get_text(separator=' ')
    text = html.unescape(text).replace('\xa0', ' ').replace('&nbsp;', ' ')

    # 1. Check for direct Instagram post or account links
    ig_urls = re.findall(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)/?', raw_desc)

    # 2. Check for Instagram mentions (@handle)
    all_mentions = re.findall(r'@([a-zA-Z0-9_\.]{3,30})', text)
    valid_mentions = [
        m for m in all_mentions 
        if not any(sp in m.lower() for sp in SPONSOR_FILTER)
    ]

    # 3. Check for specific event hashtags
    hashtags = [
        h for h in re.findall(r'#([a-zA-Z0-9_]{3,30})', text)
        if not any(sw in h.lower() for sw in ['infolomba', 'lombait', 'lomba', 'competition', 'event'])
    ]

    if ig_urls:
        handle = ig_urls[0]
        return f"@{handle}", f"https://www.instagram.com/{handle}/"
    elif valid_mentions:
        handle = valid_mentions[0]
        return f"@{handle}", f"https://www.instagram.com/{handle}/"
    elif hashtags:
        tag = hashtags[0]
        return f"#{tag}", f"https://www.instagram.com/explore/tags/{tag.lower()}/"
    else:
        clean_title = re.sub(r'[^a-zA-Z0-9 ]', '', title).strip()
        q = clean_title.replace(' ', '+')
        short_org = clean_title.split()[0] if clean_title else "Kampus"
        return f"@{short_org}", f"https://www.instagram.com/explore/search/keyword/?q={q}"

def fetch_from_tech_rss(feed_url: str, source_name: str = "Instagram Kampus") -> List[Dict[str, Any]]:
    """Fetches Indonesian campus tech competition posts and transforms them into authentic Instagram posts."""
    import html
    entries = []

    # First attempt: feedparser
    try:
        import feedparser
        feed = feedparser.parse(feed_url)
        entries = feed.entries
    except Exception:
        pass

    # Second attempt fallback: requests + BeautifulSoup
    if not entries:
        try:
            import requests
            from bs4 import BeautifulSoup
            r = requests.get(feed_url, timeout=10)
            soup = BeautifulSoup(r.text, 'xml')
            for item in soup.find_all('item'):
                entries.append(item)
        except Exception as e:
            logger.error(f"Error fetching tech RSS from {feed_url}: {e}")
            return []

    posts = []
    for entry in entries:
        try:
            # Handle BeautifulSoup Tag vs feedparser entry
            if hasattr(entry, 'find') and callable(entry.find):
                title = entry.find('title').text if entry.find('title') else "Lomba Kampus Indonesia"
                orig_link = entry.find('link').text if entry.find('link') else ""
                post_id = orig_link or title
                raw_summary = entry.find('description').text if entry.find('description') else ""
                pub_date = entry.find('pubDate').text if entry.find('pubDate') else datetime.utcnow().isoformat()
            else:
                title = getattr(entry, "title", "Lomba Kampus Indonesia")
                post_id = getattr(entry, "id", getattr(entry, "link", None))
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                orig_link = getattr(entry, "link", "")
                pub_date = getattr(entry, "published", datetime.utcnow().isoformat())

            if not post_id:
                continue

            # Extract high-res poster image URL if available
            image_url = None
            imgs = re.findall(r'<img[^>]+src=[\x22\x27]([^\x22\x27]+)[\x22\x27]', raw_summary)
            if imgs:
                image_url = imgs[0]
            elif hasattr(entry, "media_content") and entry.media_content:
                image_url = entry.media_content[0].get("url")
            elif hasattr(entry, "enclosures") and entry.enclosures:
                image_url = entry.enclosures[0].get("href")

            # Clean HTML tags and remove all external aggregator URLs
            clean_summary = re.sub(r'<[^>]+>', ' ', raw_summary)
            clean_summary = html.unescape(clean_summary).replace('\xa0', ' ').replace('&nbsp;', ' ')
            clean_summary = re.sub(r'https?://(?:www\.)?infolombait\.com[^\s]+', '', clean_summary, flags=re.IGNORECASE)
            clean_summary = ' '.join(clean_summary.split()).strip()

            # Extract pure Instagram handle & Instagram link
            organizer, ig_url = extract_instagram_details(title, raw_summary, orig_link)

            combined_text = f"{title} {clean_summary} {organizer}"

            posts.append({
                "id": post_id,
                "account": organizer,
                "title": title,
                "caption": clean_summary,
                "url": ig_url,  # Direct pure Instagram URL!
                "image_url": image_url,
                "combined_text": combined_text,
                "published_at": pub_date
            })
        except Exception as item_err:
            logger.debug(f"Error parsing feed entry: {item_err}")

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

_L_INSTANCE = None

def get_instaloader_instance() -> Optional[Any]:
    """Provides a singleton Instaloader instance with session reuse."""
    global _L_INSTANCE
    if _L_INSTANCE is not None:
        return _L_INSTANCE

    try:
        import instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
            quiet=True
        )

        if config.IG_USERNAME and config.IG_PASSWORD:
            session_file = f".ig_session_{config.IG_USERNAME}"
            try:
                L.load_session_from_file(config.IG_USERNAME, filename=session_file)
                logger.info(f"Loaded existing Instagram session for {config.IG_USERNAME}")
            except Exception:
                try:
                    L.login(config.IG_USERNAME, config.IG_PASSWORD)
                    L.save_session_to_file(filename=session_file)
                    logger.info(f"Successfully logged into Instagram as {config.IG_USERNAME} and saved session")
                except Exception as login_err:
                    logger.error(f"Failed to log in to Instagram: {login_err}")

        _L_INSTANCE = L
        return _L_INSTANCE
    except Exception as e:
        logger.warning(f"Instaloader initialization error: {e}")
        return None

def fetch_from_instaloader(account_name: str, max_posts: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches latest posts using Instaloader.
    Supports authenticated scraping from target campus accounts.
    """
    L = get_instaloader_instance()
    if not L:
        return []

    posts = []
    try:
        import instaloader
        profile = instaloader.Profile.from_username(L.context, account_name)
        count = 0
        for post in profile.get_posts():
            if count >= max_posts:
                break
            
            caption = post.caption or ""
            posts.append({
                "id": post.shortcode,
                "account": f"@{account_name}",
                "title": f"Postingan @{account_name}",
                "caption": caption,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "image_url": post.url,
                "combined_text": caption,
                "published_at": post.date_utc.isoformat() if post.date_utc else datetime.utcnow().isoformat()
            })
            count += 1
    except Exception as e:
        logger.debug(f"Could not fetch from Instagram @{account_name}: {e}")
    
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
            feed_posts = await asyncio.to_thread(fetch_from_tech_rss, feed_url, "Instagram Kampus")
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
            account=post.get("account", "Instagram Kampus"),
            url=post["url"],
            title=post.get("title", "Lomba Kampus Indonesia")
        )
        new_competitions.append(post)

    return new_competitions

