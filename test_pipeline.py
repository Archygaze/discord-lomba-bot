import asyncio
import database
import ig_monitor
import config

def test_pipeline():
    print("Initializing test database...")
    database.set_db_path("test_lomba.db")
    database.init_db()
    
    config.ENABLE_MOCK_DATA = True
    print("Testing check_new_lomba_posts with mock data...")
    posts = asyncio.run(ig_monitor.check_new_lomba_posts())
    print(f"Discovered {len(posts)} new posts.")
    for p in posts:
        print(f" - [{p['account']}] {p['title']} (Keywords: {p.get('matched_keywords')})")
        
    print("\nChecking deduplication...")
    posts_second_run = asyncio.run(ig_monitor.check_new_lomba_posts())
    print(f"Discovered on second run: {len(posts_second_run)} (Expected 0 due to SQLite tracking)")
    assert len(posts_second_run) == 0, "Deduplication failed!"
    
    recent = database.get_recent_posts(limit=2, db_path="test_lomba.db")
    print(f"Recent posts in DB: {len(recent)}")
    print("Test passed successfully!")

if __name__ == "__main__":
    test_pipeline()
