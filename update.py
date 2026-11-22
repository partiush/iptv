import os
import re
import requests
from playwright.sync_api import sync_playwright

# 1. CONFIGURATION
TRIAL_SITE_URL = "https://YOUR-TRIAL-WEBSITE.com"
BUTTON_SELECTOR = "button#generate-btn"  # Replace with the actual button selector
XTREAM_HOST = "http://YOUR-XTREAM-SERVER:8080"

# Your other static M3U playlists
OTHER_M3U_URLS = [
    "https://example.com/playlist1.m3u",
    "https://example.com/playlist2.m3u",
]

# Exact or partial names of the ~50 channels you want to keep (case-insensitive)
WANTED_CHANNELS = [
    "Star Plus",
    "Sony TV",
    "Colors",
    "Zee TV",
    "Aaj Tak",
    "NDTV India",
    "Sony SAB",
    # Add up to ~50 channel names here
]

def get_trial_credentials():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TRIAL_SITE_URL, wait_until="networkidle")
        
        # Wait 7 seconds to clear the 5-second button countdown
        page.wait_for_timeout(7000)
        
        # Click the generate button if it's visible
        if page.locator(BUTTON_SELECTOR).is_visible():
            page.locator(BUTTON_SELECTOR).click()
            page.wait_for_timeout(3000)
            
        page_text = page.inner_text("body")
        browser.close()

        # Extract Username and Password from the page text
        user_match = re.search(r"Username\s*[:\-]\s*(\S+)", page_text, re.IGNORECASE)
        pass_match = re.search(r"Password\s*[:\-]\s*(\S+)", page_text, re.IGNORECASE)

        if user_match and pass_match:
            return user_match.group(1), pass_match.group(1)
        raise Exception("Could not find Username/Password on page")

def build_filtered_playlist():
    all_urls = list(OTHER_M3U_URLS)
    
    try:
        user, pwd = get_trial_credentials()
        trial_m3u = f"{XTREAM_HOST}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"
        all_urls.insert(0, trial_m3u)
        print(f"Fetched trial account: {user}")
    except Exception as e:
        print(f"Trial fetch failed ({e}), continuing with backup playlists...")

    output_lines = ["#EXTM3U\n"]
    
    for url in all_urls:
        try:
            resp = requests.get(url, timeout=20)
            lines = resp.text.splitlines()
            for i in range(len(lines)):
                if lines[i].startswith("#EXTINF"):
                    channel_info = lines[i]
                    if any(wanted.lower() in channel_info.lower() for wanted in WANTED_CHANNELS):
                        if i + 1 < len(lines) and lines[i + 1].startswith("http"):
                            output_lines.append(channel_info + "\n")
                            output_lines.append(lines[i + 1] + "\n")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.writelines(output_lines)

if __name__ == "__main__":
    build_filtered_playlist()
