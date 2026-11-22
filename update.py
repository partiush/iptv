import re
import requests
from playwright.sync_api import sync_playwright

# 1. YOUR OTHER STATIC M3U LINKS
OTHER_M3U_URLS = [
    "https://example.com/playlist2.m3u",
    "https://example.com/playlist3.m3u",
]

# 2. YOUR ~50 FAVORITE CHANNELS (Partial or exact names, case-insensitive)
WANTED_CHANNELS = [
    "Star Plus",
    "Sony TV",
    "Colors",
    "Zee TV",
    "Sony SAB",
    "Aaj Tak",
    "NDTV India",
    "PTC Punjabi",
    # Add the rest of your ~50 channel names here
]

TRIAL_SITE_URL = "https://freeiptv2023-d.ottc.xyz"
XTREAM_HOST = "http://freeiptv.ottc.xyz:80"


def get_freeiptv_m3u():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()
        page.goto(TRIAL_SITE_URL, wait_until="domcontentloaded", timeout=30000)

        # Wait 8 seconds to clear the 5-second unlock countdown
        page.wait_for_timeout(8000)

        # Click "Create free IPTV account !" if present (matches button, link, or div)
        create_btn = page.get_by_text("Create free IPTV account", exact=False)
        if create_btn.count() > 0:
            create_btn.first.click()
            page.wait_for_timeout(5000)

        # Grab both visible text and raw HTML so truncated visual text won't break extraction
        page_text = page.inner_text("body")
        page_html = page.content()
        browser.close()

        # Method A: Extract full M3U link directly from the HTML
        m3u_match = re.search(
            r'(http://freeiptv\.ottc\.xyz:80/get\.php\?[^"\'\s<]+)', page_html
        )
        if m3u_match:
            return m3u_match.group(1).replace("&amp;", "&")

        # Method B: Fallback to extracting IPTV Username and IPTV Password
        user_match = re.search(r"IPTV Username\s+(\d+)", page_text)
        pass_match = re.search(r"IPTV Password\s+(\d+)", page_text)
        if user_match and pass_match:
            user, pwd = user_match.group(1), pass_match.group(1)
            return f"{XTREAM_HOST}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"

        raise Exception(f"Could not extract credentials. Page snippet:\n{page_text[:400]}")


def build_filtered_playlist():
    all_urls = list(OTHER_M3U_URLS)

    try:
        trial_m3u = get_freeiptv_m3u()
        all_urls.insert(0, trial_m3u)
        print(f"Successfully fetched fresh freeiptv link: {trial_m3u}")
    except Exception as e:
        print(f"Warning - freeiptv fetch failed: {e}")

    output_lines = ["#EXTM3U\n"]
    matched_count = 0

    for url in all_urls:
        try:
            resp = requests.get(url, timeout=25)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            for i in range(len(lines)):
                if lines[i].startswith("#EXTINF"):
                    channel_info = lines[i]
                    if any(w.lower() in channel_info.lower() for w in WANTED_CHANNELS):
                        if i + 1 < len(lines) and lines[i + 1].startswith("http"):
                            output_lines.append(channel_info + "\n")
                            output_lines.append(lines[i + 1] + "\n")
                            matched_count += 1
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"Saved playlist.m3u with {matched_count} channels.")


if __name__ == "__main__":
    build_filtered_playlist()
