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

# Instagram Monitored Accounts (comma-separated usernames without @)
DEFAULT_ACCOUNTS = "hackathon_id,infolomba,lombanasional,eventkampus"
raw_accounts = os.getenv("TARGET_ACCOUNTS") or DEFAULT_ACCOUNTS
TARGET_ACCOUNTS = [
    acc.strip().lstrip("@")
    for acc in raw_accounts.split(",")
    if acc.strip()
]

# RSS / RSSHub Configuration (optional, highly recommended for reliable scraping)
# e.g., if you have an RSSHub instance: https://rsshub.app/instagram/user/{username}
# Or RSS.app feeds
RSS_FEED_TEMPLATE = os.getenv("RSS_FEED_TEMPLATE", "")

# Keywords to identify hackathon/competition posts (comma-separated, case-insensitive)
DEFAULT_KEYWORDS = (
    "hackathon,lomba,kompetisi,competition,coding,datathon,ideathon,ctf,"
    "capture the flag,ui/ux,web development,software engineering,cyber security,"
    "open registration,registrasi dibuka,hadiah jutaan,total hadiah"
)
RAW_KEYWORDS = os.getenv("KEYWORDS", DEFAULT_KEYWORDS)
KEYWORDS = [k.strip().lower() for k in RAW_KEYWORDS.split(",") if k.strip()]
ENABLE_KEYWORD_FILTER = os.getenv("ENABLE_KEYWORD_FILTER", "true").lower() in ("1", "true", "yes")

# Instaloader credentials (optional; leave blank for anonymous / mock / RSS)
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")

# Mock Mode (useful for testing embeds and pings immediately without real IG connection)
ENABLE_MOCK_DATA = os.getenv("ENABLE_MOCK_DATA", "false").lower() in ("1", "true", "yes")
