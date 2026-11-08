import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is not None and val.strip().isdigit():
        return int(val.strip())
    return default

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
DISCORD_CHANNEL_ID = _get_int("DISCORD_CHANNEL_ID", 0)
DISCORD_PING_ROLE_ID = os.getenv("DISCORD_PING_ROLE_ID", "").strip()

# Checking Schedule (in minutes)
CHECK_INTERVAL_MINUTES = _get_int("CHECK_INTERVAL_MINUTES", 30)

# Instagram Monitored Accounts (Indonesian Campus IT Events & Hubs)
DEFAULT_ACCOUNTS = (
    "compfest,arkavidia,finditugm,schematics.its,hology_ub,"
    "jointsugm,technofair,mage_its,it_today_ipb,dinamik_upi,"
    "lomba_it,infolombamahasiswa,infolomba"
)
raw_accounts = os.getenv("TARGET_ACCOUNTS") or DEFAULT_ACCOUNTS
TARGET_ACCOUNTS = [
    acc.strip().lstrip("@")
    for acc in raw_accounts.split(",")
    if acc.strip()
]

# Dedicated Indonesian Campus Tech RSS Feeds (Hackathons, UI/UX, CTF, IT Competitions)
DEFAULT_TECH_FEEDS = "https://www.infolombait.com/feeds/posts/default?alt=rss"
raw_feeds = os.getenv("TECH_RSS_FEEDS") or DEFAULT_TECH_FEEDS
TECH_RSS_FEEDS = [f.strip() for f in raw_feeds.split(",") if f.strip()]

# RSS / RSSHub Configuration (optional template for Instagram accounts)
# e.g., if you have an RSSHub instance: https://rsshub.app/instagram/user/{username}
RSS_FEED_TEMPLATE = os.getenv("RSS_FEED_TEMPLATE", "")

# Keywords to identify campus tech/hackathon posts (case-insensitive)
DEFAULT_KEYWORDS = (
    "hackathon,hackfest,ui/ux,ui ux,ux design,ui design,user experience,user interface,"
    "product design,ctf,capture the flag,cyber security,cybersecurity,keamanan siber,"
    "infosec,competitive programming,coding,algoritma,pemrograman,data science,datathon,"
    "data analytics,machine learning,artificial intelligence,ai,software engineering,"
    "software development,web development,web dev,web design,mobile dev,mobile app,android,"
    "ios,game dev,game development,iot,internet of things,lomba it,kompetisi it,tech competition,"
    "lomba teknologi,it case,business it,it contest,ideation tech,network computer"
)
RAW_KEYWORDS = os.getenv("KEYWORDS", DEFAULT_KEYWORDS)
KEYWORDS = [k.strip().lower() for k in RAW_KEYWORDS.split(",") if k.strip()]
ENABLE_KEYWORD_FILTER = os.getenv("ENABLE_KEYWORD_FILTER", "true").lower() in ("1", "true", "yes")

# Instaloader credentials (optional; leave blank for anonymous / mock / RSS)
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")

# Mock Mode (useful for testing embeds and pings immediately without real IG connection)
ENABLE_MOCK_DATA = os.getenv("ENABLE_MOCK_DATA", "false").lower() in ("1", "true", "yes")
