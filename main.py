import json
from bs4 import BeautifulSoup
import requests


def main():
  home_url = "https://m.crichd.pk/"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/120.0.0.0 Safari/537.36"
      )
  }

  print("হোম পেজ থেকে তথ্য সংগ্রহ করা হচ্ছে...")
  response = requests.get(home_url, headers=headers)
  if response.status_code != 200:
    print("হোম পেজ লোড করা যায়নি!")
    return

  soup = BeautifulSoup(response.text, "html.parser")
  matches_data = []

  # হোমপেজের প্রতিটি ম্যাচ কার্ড বা লিংক খুঁজে বের করা
  for card in soup.select("a[href*='/event/'], a[href*='/watch/']"):
    container = card.find_parent(["div", "li"], class_=lambda x: x and "flex" in x) or card.parent

    href = card.get("href", "")
    if not href:
      continue
    detail_url = (
        href if href.startswith("http") else "https://m.crichd.pk/" + href
    )

    # ১. ইভেন্ট বা সময়ের নাম (যেমন: Live Now! বা Starts in: ...)
    time_elem = container.find(
        text=lambda t: t and ("Live" in t or "Starts" in t)
    )
    event_name = time_elem.strip() if time_elem else "Live Sports"

    # ২. টিমের লোগো সংগ্রহ
    logos = []
    for img in container.select("img"):
      src = img.get("src", "")
      if src:
        logos.append(src)

    # ৩. সঠিক টিমের নাম সংগ্রহ
    texts = [
        el.get_text(strip=True)
        for el in container.select("div, span, b, p")
        if el.get_text(strip=True)
        and "Live" not in el.get_text()
        and "Starts" not in el.get_text()
    ]

    filtered_teams = []
    for t in texts:
      if len(t) > 2 and t not in filtered_teams and t != event_name:
        filtered_teams.append(t)

    team1_name = filtered_teams[0] if len(filtered_teams) > 0 else "Team 1"
    team2_name = filtered_teams[1] if len(filtered_teams) > 1 else "Team 2"

    team1_logo = logos[0] if len(logos) > 0 else ""
    team2_logo = logos[1] if len(logos) > 1 else ""

    matches_data.append({
        "event_name": event_name,
        "team1_name": team1_name,
        "team2_name": team2_name,
        "team1_logo": team1_logo,
        "team2_logo": team2_logo,
        "detail_url": detail_url,
    })

  # ডুপ্লিকেট বাদ দেওয়া
  seen_urls = set()
  unique_matches = []
  for m in matches_data:
    if m["detail_url"] not in seen_urls:
      seen_urls.add(m["detail_url"])
      unique_matches.append(m)

  # JSON ফাইলে সেভ করা
  with open("crichd_matches.json", "w", encoding="utf-8") as f:
    json.dump(unique_matches, f, indent=4, ensure_ascii=False)

  print(
      f"মোট {len(unique_matches)} টি ম্যাচের তথ্য সফলভাবে 'crichd_matches.json'"
      " ফাইলে সেভ করা হয়েছে!"
  )


if __name__ == "__main__":
  main()
