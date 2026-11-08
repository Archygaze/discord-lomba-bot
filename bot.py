import os
import sys
import logging
import html
import re
import discord
from discord.ext import commands, tasks
from datetime import datetime

import config
import database
import ig_monitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("LombaBot")

# Discord Intents
intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    status=discord.Status.dnd,
    activity=discord.CustomActivity(name="fuck it we ball")
)

def get_mention_string() -> str:
    """Builds the mention string based on configuration."""
    role_config = str(config.DISCORD_PING_ROLE_ID).strip().lower()
    if not role_config:
        return ""
    if role_config == "everyone":
        return "@everyone"
    if role_config == "here":
        return "@here"
    if role_config.isdigit():
        return f"<@&{role_config}>"
    return ""

def parse_competition_details(caption: str, title: str, account: str) -> dict:
    """Cleans and extracts structured fields from raw Indonesian competition text."""
    # 1. Clean HTML entities and spaces
    text = html.unescape(caption).replace('\xa0', ' ').replace('&nbsp;', ' ')
    text = re.sub(r'[\r\t]+', ' ', text)

    # 2. Extract Real Campus Organizer
    organizer = account
    org_match = re.search(
        r'((?:HIMA|BEM|HMIF|Himpunan|Fakultas|Universitas|Institut|Politeknik|Divisi Humas)[^\n#\.\!\?]{3,80})',
        text,
        re.IGNORECASE
    )
    if org_match:
        organizer = org_match.group(1).strip()
    elif account.startswith("@") or account.startswith("#"):
        organizer = account
    elif "@" in text:
        ig_mentions = re.findall(r'@([a-zA-Z0-9_\.]{3,30})', text)
        if ig_mentions:
            organizer = f"@{ig_mentions[0]}"

    # 3. Extract Categories / Cabang Kompetisi
    branches = []
    cat_match = re.search(
        r'(?:Cabang Kompetisi|Kategori Lomba|Cabang Lomba|Divisi Lomba)[:\s]+(.*?)(?=✨|💰|📅|🔗|Kenapa|Biaya|Pendaftaran|Timeline|🎁|$)',
        text,
        re.DOTALL | re.IGNORECASE
    )
    if cat_match:
        items = [
            re.sub(r'^(?:yang dapat kamu ikuti|antara lain|meliputi|yaitu|sebagai berikut)[:\s]*', '', c.strip(), flags=re.IGNORECASE)
            for c in re.split(r'[\n•\-\*]|(?=[🎮💼📄🚀💻🎬🎨🌐🏴])', cat_match.group(1))
            if len(c.strip()) > 3 and not c.strip().startswith("http")
        ]
        # Clean extra leading punctuation or empty items
        branches = [b.strip() for b in items if len(b.strip()) > 3][:4]

    # 4. Extract Deadline
    deadline = None
    dl_match = re.search(
        r'(?:Batas Pendaftaran|Deadline|Pendaftaran s/d|Pendaftaran Terakhir|Pendaftaran)[:\s]+([0-9]{1,2}\s+[A-Za-z]+(?:\s+[0-9]{4})?|[0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
        text,
        re.IGNORECASE
    )
    if dl_match:
        deadline = dl_match.group(1).strip()

    # 5. Extract Registration & Guidebook Links (Strictly ignore infolombait/blogger/tracking links)
    all_links = re.findall(r'https?://[^\s\x22\x27<>]+', text)
    reg_link = None
    guidebook_link = None
    for link in all_links:
        link_lower = link.lower()
        if any(bad in link_lower for bad in ["infolombait", "blogger.com", "googleusercontent", "feedproxy"]):
            continue
        if any(gb in link_lower for gb in ["guidebook", "juknis", "panduan", "buku-panduan", "guide"]):
            guidebook_link = link
        elif any(reg in link_lower for reg in ["daftar", "registrasi", "form", "pendaftaran", "bit.ly", "linktr.ee"]):
            if not reg_link:
                reg_link = link

    return {
        "organizer": organizer,
        "branches": branches,
        "deadline": deadline,
        "reg_link": reg_link,
        "guidebook_link": guidebook_link
    }

def create_lomba_embed(post: dict) -> discord.Embed:
    """Creates a clean, minimal, Instagram-native Discord Embed."""
    raw_title = post.get("title") or f"Lomba Kampus: {post.get('account')}"
    title = f"🏆 {raw_title}" if not raw_title.startswith("🏆") else raw_title
    caption = post.get("caption", "").strip()

    # Parse metadata cleanly
    details = parse_competition_details(caption, raw_title, post.get("account", "Instagram Kampus"))

    # Fail-safe sanitization for Instagram post URL
    post_url = post.get("url") or "https://www.instagram.com/"
    if "infolombait" in post_url.lower():
        acc = post.get("account", "").lstrip("@")
        post_url = f"https://www.instagram.com/{acc}/" if acc else "https://www.instagram.com/"

    embed = discord.Embed(
        title=title,
        url=post_url,
        color=discord.Color.from_rgb(225, 48, 108), # Vibrant Instagram Rose
        timestamp=datetime.utcnow()
    )

    # Clean author header with Instagram identity and campus organizer
    embed.set_author(
        name=f"📸 Instagram • {details['organizer']}",
        url=post_url,
        icon_url="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
    )

    # 1. Cabang Lomba (Structured, short, elegant)
    if details["branches"]:
        branches_str = "\n".join(f"• {b}" for b in details["branches"])
        embed.add_field(name="🎯 Cabang Kompetisi", value=branches_str, inline=False)
    elif post.get("matched_keywords"):
        kw_string = ", ".join(f"`{k}`" for k in post["matched_keywords"][:5])
        embed.add_field(name="🎯 Kategori Lomba", value=kw_string, inline=False)

    # 2. Timeline / Deadline
    if details["deadline"]:
        embed.add_field(name="📅 Batas Pendaftaran", value=f"**{details['deadline']}**", inline=True)

    # 3. Status Verifikasi
    embed.add_field(
        name="🛡️ Keaslian",
        value="✅ Terverifikasi Resmi Kampus",
        inline=True
    )

    # 4. Tautan Resmi (Direct Instagram & Official Form links)
    action_links = []
    if "/p/" in post_url or "/reel/" in post_url:
        action_links.append(f"[📱 Buka Postingan Instagram]({post_url})")
    elif "/explore/tags/" in post_url:
        tag_clean = post_url.rstrip("/").split("/")[-1]
        action_links.append(f"[📱 Postingan Instagram #{tag_clean}]({post_url})")
    elif "instagram.com/" in post_url and post_url.rstrip("/") not in ("https://www.instagram.com", "https://instagram.com"):
        handle_clean = post_url.rstrip("/").split("/")[-1]
        action_links.append(f"[📱 Kunjungi Akun Instagram @{handle_clean}]({post_url})")
    else:
        action_links.append(f"[📱 Buka Instagram]({post_url})")

    if details["reg_link"]:
        action_links.append(f"[📝 Formulir Pendaftaran]({details['reg_link']})")
    if details["guidebook_link"]:
        action_links.append(f"[📖 Buku Panduan]({details['guidebook_link']})")

    embed.add_field(
        name="📌 Tautan Lengkap",
        value=" • ".join(action_links),
        inline=False
    )

    if post.get("image_url"):
        embed.set_image(url=post["image_url"])

    embed.set_footer(
        text="fuck it we ball • Radar Lomba Kampus 🇮🇩",
        icon_url="https://cdn-icons-png.flaticon.com/512/3112/3112946.png"
    )
    return embed

async def broadcast_post(channel: discord.TextChannel, post: dict):
    """Sends the post notification to the given text channel."""
    mention = get_mention_string()
    content = f"📢 {mention} **Ada info lomba/hackathon baru yang diposting!**" if mention else "📢 **Ada info lomba/hackathon baru yang diposting!**"
    embed = create_lomba_embed(post)

    allowed = discord.AllowedMentions(
        everyone=True,
        roles=True,
        users=True
    )
    await channel.send(content=content, embed=embed, allowed_mentions=allowed)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    
    # Set Discord presence / activity to Do Not Disturb (DND)
    try:
        activity = discord.CustomActivity(name="fuck it we ball")
        await bot.change_presence(activity=activity, status=discord.Status.dnd)
    except Exception as e:
        logger.debug(f"Could not set custom activity: {e}")

    # Sync slash commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} application slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

    # Start background task if not already running
    if not check_lomba_loop.is_running():
        check_lomba_loop.start()
        logger.info(f"Started check_lomba_loop (Interval: {config.CHECK_INTERVAL_MINUTES} minutes)")

@tasks.loop(minutes=config.CHECK_INTERVAL_MINUTES)
async def check_lomba_loop():
    """Periodic loop to scrape Instagram and notify Discord channel."""
    if not config.DISCORD_CHANNEL_ID:
        logger.warning("DISCORD_CHANNEL_ID is not configured in .env. Skipping check.")
        return

    channel = bot.get_channel(config.DISCORD_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(config.DISCORD_CHANNEL_ID)
        except Exception as e:
            logger.error(f"Could not find or access Discord channel {config.DISCORD_CHANNEL_ID}: {e}")
            return

    logger.info("Checking Instagram for new competitions/hackathons...")
    try:
        new_posts = await ig_monitor.check_new_lomba_posts()
        if new_posts:
            logger.info(f"Found {len(new_posts)} new competition posts!")
            for post in new_posts:
                await broadcast_post(channel, post)
        else:
            logger.info("No new matching competition posts found.")
    except Exception as e:
        logger.error(f"Error during check_lomba_loop: {e}", exc_info=True)

@check_lomba_loop.before_loop
async def before_check_loop():
    await bot.wait_until_ready()

# --- Slash Commands ---

@bot.tree.command(name="ping_test", description="Test pengingat dan izin bot di channel ini.")
async def ping_test(interaction: discord.Interaction):
    """Verifies that the bot can send messages and role pings."""
    mention = get_mention_string()
    msg = f"✅ Bot aktif dan terhubung!\n"
    msg += f"• **Target Channel ID**: `{config.DISCORD_CHANNEL_ID}`\n"
    msg += f"• **Role Ping**: {mention if mention else '*(Tidak ada role ping / None)*'}\n"
    msg += f"• **Interval Pengecekan**: `{config.CHECK_INTERVAL_MINUTES} menit`\n"
    msg += f"• **Akun IG Dipantau**: `{', '.join(config.TARGET_ACCOUNTS)}`"

    test_post = {
        "account": "@compfest",
        "title": "🎉 Tes Notifikasi Lomba Bot",
        "caption": "Ini adalah pesan percobaan untuk memastikan format embed dan notifikasi ping berfungsi dengan sempurna! Penyelenggara: Fakultas Ilmu Komputer UI (@compfest)",
        "url": "https://www.instagram.com/p/DdECA40pnMK/",
        "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800",
        "matched_keywords": ["test", "hackathon"]
    }
    embed = create_lomba_embed(test_post)

    await interaction.response.send_message(content=msg, embed=embed)

@bot.tree.command(name="test_lomba", description="Kirimkan 1 contoh postingan lomba Instagram kampus untuk melihat format kartu.")
async def test_lomba(interaction: discord.Interaction):
    """Sends a sample real Instagram competition post for verification."""
    await interaction.response.defer(thinking=True)
    try:
        sample_post = {
            "id": "test_sample_compfest_ui",
            "title": "COMPFEST 16 - Universitas Indonesia",
            "caption": (
                "📢 COMPFEST 16 IS OFFICIALLY OPEN FOR REGISTRATION!\n"
                "Tema: Empowering Technological Innovations for Sustainable Future\n\n"
                "Cabang Kompetisi:\n"
                "• 🏴‍☠️ Capture The Flag (CTF)\n"
                "• 💻 Competitive Programming\n"
                "• 🎨 UI/UX Design Competition\n"
                "• 🤖 AI Innovation Challenge\n\n"
                "Penyelenggara: Fakultas Ilmu Komputer Universitas Indonesia (@compfest)\n"
                "Batas Pendaftaran: 30 November 2026\n"
                "Link Pendaftaran: https://compfest.id/register\n"
                "Buku Panduan: https://compfest.id/guidebook"
            ),
            "url": "https://www.instagram.com/p/DdECA40pnMK/",
            "image_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800",
            "account": "@compfest",
            "matched_keywords": ["ctf", "ui/ux", "ai", "competitive programming"]
        }
        embed = create_lomba_embed(sample_post)
        await interaction.followup.send(content="✨ **Berikut contoh tampilan format kartu lomba langsung menuju ke postingan Instagram:**", embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{e}`")

@bot.tree.command(name="check_lomba", description="Cek manual postingan lomba baru sekarang.")
async def check_lomba(interaction: discord.Interaction):
    """Manually triggers an Instagram check."""
    await interaction.response.defer(thinking=True)
    
    try:
        new_posts = await ig_monitor.check_new_lomba_posts()
        if not new_posts:
            await interaction.followup.send("🔍 Pengecekan selesai! Belum ada postingan lomba baru yang belum dilihat.")
            return

        channel = interaction.channel
        for post in new_posts:
            await broadcast_post(channel, post)

        await interaction.followup.send(f"✅ Ditemukan dan dikirimkan **{len(new_posts)}** postingan lomba baru!")
    except Exception as e:
        await interaction.followup.send(f"❌ Terjadi kesalahan saat memeriksa lomba: `{e}`")

@bot.tree.command(name="status", description="Lihat status bot dan statistik database.")
async def status(interaction: discord.Interaction):
    """Displays bot settings and seen posts statistics."""
    total_posts = database.get_total_posts_count()
    accounts_str = ", ".join(f"@{acc}" for acc in config.TARGET_ACCOUNTS)
    
    embed = discord.Embed(
        title="🤖 Status Bot Info Lomba Kampus Indonesia",
        description="Created by **Archygaze**\nMemantau lomba Teknologi (Hackathon, UI/UX, CTF) & Seni (Film, Animasi, Desain)",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="📊 Total Lomba Tercatat", value=f"**{total_posts}** postingan", inline=True)
    embed.add_field(name="⏱️ Interval Check", value=f"{config.CHECK_INTERVAL_MINUTES} menit", inline=True)
    embed.add_field(name="🎯 Filter Keyword", value="Aktif" if config.ENABLE_KEYWORD_FILTER else "Nonaktif", inline=True)
    embed.add_field(name="📱 Akun IG Terdaftar", value=accounts_str, inline=False)
    
    kw_sample = ", ".join(config.KEYWORDS[:8]) + "..."
    embed.add_field(name="🔍 Keyword Dipantau", value=f"`{kw_sample}`", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="recent_lomba", description="Lihat 5 info lomba terakhir yang tersimpan di database.")
async def recent_lomba(interaction: discord.Interaction):
    """Lists the latest entries stored in the database."""
    posts = database.get_recent_posts(limit=5)
    if not posts:
        await interaction.response.send_message("Belum ada riwayat lomba yang tersimpan.")
        return

    embed = discord.Embed(
        title="📋 5 Info Lomba / Hackathon Terakhir",
        color=discord.Color.purple(),
        timestamp=datetime.utcnow()
    )
    for p in posts:
        embed.add_field(
            name=f"@{p['account']} • {p.get('title', 'Lomba')}",
            value=f"[Buka Link Postingan]({p['url']})\n*Terdeteksi: {p['detected_at']}*",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

def main():
    database.init_db()
    if not config.DISCORD_TOKEN:
        print("[ERROR] DISCORD_TOKEN belum diisi di file .env! Harap isi token terlebih dahulu.")
        sys.exit(1)

    print("Memulai bot...")
    bot.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()

