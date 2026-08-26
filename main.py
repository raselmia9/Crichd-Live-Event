import asyncio
import json
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests


async def main():
  home_url = "https://m.crichd.pk/"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36"
      )
  }

  print("হোম পেজ থেকে ম্যাচ লিস্ট সংগ্রহ করা হচ্ছে...")
  response = requests.get(home_url, headers=headers)
  if response.status_code != 200:
    print("হোম পেজ লোড করা যায়নি!")
    return

  soup = BeautifulSoup(response.text, "html.parser")
  matches_data = []

  # হোম পেজ থেকে ইভেন্ট বা ম্যাচ কার্ডের লিংকগুলো খুঁজে বের করা
  for card in soup.select("a"):
    href = card.get("href", "")
    if "/event/" in href or "/watch/" in href:
      detail_url = href if href.startswith("http") else "https://m.crichd.pk" + href

      parent_card = card.find_parent()
      if not parent_card:
        continue

      # ১. ইভেন্টের নাম
      event_elem = parent_card.select_one(
          ".event-name, h3, .league-title, span"
      )
      event_name = event_elem.text.strip() if event_elem else "Live Sports"

      # ২ ও ৪. টিম ১ ও টিম ২ এর নাম
      teams = parent_card.select(".team-name, div span")
      team1_name = teams[0].text.strip() if len(teams) > 0 else "Team 1"
      team2_name = teams[1].text.strip() if len(teams) > 1 else "Team 2"

      # ৩. টিম ১ ও টিম ২ এর লোগো
      logos = parent_card.select("img")
      team1_logo = logos[0]["src"] if len(logos) > 0 else ""
      team2_logo = logos[1]["src"] if len(logos) > 1 else ""

      matches_data.append({
          "detail_url": detail_url,
          "event_name": event_name,
          "team1_name": team1_name,
          "team2_name": team2_name,
          "team1_logo": team1_logo,
          "team2_logo": team2_logo,
      })

  # ডুপ্লিকেট ইউআরএল বাদ দেওয়া
  seen_urls = set()
  unique_matches = []
  for m in matches_data:
    if m["detail_url"] not in seen_urls:
      seen_urls.add(m["detail_url"])
      unique_matches.append(m)

  print(
      f"মোট {len(unique_matches)} টি ম্যাচ পাওয়া গেছে। ডিটেইলস ও স্ট্রিম লিংক"
      " সংগ্রহ করা হচ্ছে..."
  )

  final_output = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()

    for match in unique_matches:
      page = await context.new_page()
      # গতি বাড়ানোর জন্য ইমেজ ও সিএসএস ব্লক করা
      await page.route(
          "**/*.{png,jpg,jpeg,gif,css,svg}", lambda route: route.abort()
      )

      match_date_time = "N/A"
      streams_list = []

      def handle_request(request):
        nonlocal streams_list
        if ".m3u8" in request.url:
          stream_url = request.url
          referer_url = request.headers.get("referer", "https://crichdsee.st/")

          # লিংক নাম সিরিয়াল অনুযায়ী তৈরি করা (Link1, Link2...)
          link_name = f"Link{len(streams_list) + 1}"
          formatted_stream = (
              f"{link_name},,{stream_url}|Referer={referer_url},"
          )

          if formatted_stream not in streams_list:
            streams_list.append(formatted_stream)

      page.on("request", handle_request)

      try:
        await page.goto(match["detail_url"], timeout=20000)

        # ৫. তারিখ এবং সময় সংগ্রহ করা
        date_elem = await page.query_selector(
            ".date-time, .schedule-date, span"
        )
        if date_elem:
          match_date_time = await date_elem.inner_text()

        # চ্যানেল অপশনগুলোতে ক্লিক করে m3u8 লিংক ট্রিগার করা
        channel_links = await page.query_selector_all(
            "table tr td a, .channels-list a"
        )
        for link in channel_links[:3]:  # প্রথম ৩টি চ্যানেল চেক করা
          try:
            await link.click()
            await asyncio.sleep(2)
          except:
            pass

      except Exception as e:
        print(f"Error for {match['detail_url']}: {e}")

      await page.close()

      # মাল্টি-স্ট্রিমিং লিংকগুলোকে আপনার কাঙ্ক্ষিত কমা-সেপারেটেড ফরম্যাটে জোড়া লাগানো
      multi_streaming_str = (
          ")".join(streams_list) + ")" if streams_list else ""
      )

      # চূড়ান্ত ডেটা স্ট্রাকচার
      final_output.append({
          "event_name": match["event_name"],
          "team1_logo": match["team1_logo"],
          "team2_logo": match["team2_logo"],
          "team1_name": match["team1_name"],
          "team2_name": match["team2_name"],
          "date_and_time": match_date_time.strip(),
          "multi_streaming": multi_streaming_str,
      })

    await browser.close()

  # JSON ফাইলে ডেটা সেভ করা
  with open("crichd_matches.json", "w", encoding="utf-8") as f:
    json.dump(final_output, f, indent=4, ensure_ascii=False)

  print("সফলভাবে 'crichd_matches.json' ফাইলে ডেটা সেভ করা হয়েছে!")


if __name__ == "__main__":
  asyncio.run(main())
