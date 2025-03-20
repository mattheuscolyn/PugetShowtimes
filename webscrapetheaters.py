import requests
import re
import csv
import time
import math
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

CURRENT_YEAR = datetime.now().year
showtimes_data = []

# Session for efficient requests
session = requests.Session()
session.headers.update(HEADERS)


def format_date(date_str, year):
    """Convert a date string into mm/dd/yyyy format, assuming a given year."""
    try:
        return datetime.strptime(f"{date_str} {year}", "%B %d %Y").strftime("%m/%d/%Y")
    except ValueError:
        return None


### --- Scraping The Beacon --- ###
def scrape_beacon():
    url = "https://thebeacon.film/calendar"
    response = session.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}")
        return

    beacon_links = set(re.findall(r"'(https://thebeacon\.film/calendar/movie/[^\']+)'", response.text))

    for link in beacon_links:
        soup = BeautifulSoup(session.get(link).text, "html.parser")
        movie_title = soup.title.string.split(" | ")[0] if soup.title else "Unknown Movie"

        # Extract runtime
        runtime = next(
            (div.find("p").get_text(strip=True).replace(" minutes", "")
             for div in soup.find_all("div", class_="w-8")
             if div.find("h4") and "Runtime" in div.find("h4").text),
            "Unknown"
        )

        # Extract showtimes
        for div in soup.find_all("div", class_="showtime_item transformer showtime_exists"):
            if not div.get("data-value"):
                continue
            date, showtime_time = div.get_text(strip=True, separator=" ").rsplit(" ", 1)
            formatted_date = format_date(date.split(",")[-1].strip(), CURRENT_YEAR)
            if formatted_date:
                showtimes_data.append([formatted_date, showtime_time, "The Beacon", movie_title, runtime, "None", "None"])


### --- Scraping SIFF Cinema --- ###
def scrape_siff():
    base_url = "https://www.siff.net"
    main_url = f"{base_url}/cinema/in-theaters"
    
    response = session.get(main_url)
    if response.status_code != 200:
        print(f"Failed to fetch {main_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    movie_links = {base_url + a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("/cinema/in-theaters/")}

    for movie_url in movie_links:
        soup = BeautifulSoup(session.get(movie_url).text, "html.parser")
        movie_title = soup.title.string if soup.title else "Unknown Movie"
        movie_year = next((int(m.group(1)) for m in re.finditer(r"(\d{4})", soup.text)), CURRENT_YEAR)

        for day_div in soup.find_all("div", class_="day"):
            date_tag = day_div.find("p", class_="h3")
            formatted_date = format_date(date_tag.get_text(strip=True).split(",")[-1].strip(), movie_year) if date_tag else None

            if not formatted_date:
                continue

            for showtime_item in day_div.find_all("div", class_="item small-copy"):
                venue = (showtime_item.find("h4").get_text(strip=True) if showtime_item.find("h4") else "Unknown Venue")
                times = [a.get_text(strip=True).replace(" ", "") for a in showtime_item.find_all("a", id=lambda x: x and x.startswith("screening-"))]

                for showtime_time in times:
                    showtimes_data.append([formatted_date, showtime_time, venue, movie_title, "Unknown", "None", "None"])


### --- Scraping AMC Theaters --- ###
AMC_BASE_URL = "https://api.amctheatres.com/v2"
AMC_API_KEY = "x"
AMC_HEADERS = {"X-AMC-Vendor-Key": AMC_API_KEY}
SEATTLE_LAT, SEATTLE_LON, RADIUS_MILES, DAYS_AHEAD = 47.6062, -122.3321, 300, 5


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two latitude/longitude points."""
    R = 3958.8  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_all_theaters():
    """Fetch all AMC theaters."""
    theaters = []
    url = f"{AMC_BASE_URL}/theatres?page-number=1&page-size=50"

    while url:
        response = session.get(url, headers=AMC_HEADERS)
        if response.status_code != 200:
            print("Error fetching theaters:", response.text)
            break

        data = response.json()
        theaters.extend(data["_embedded"].get("theatres", []))
        url = data["_links"].get("next", {}).get("href")

    return theaters


def get_showtimes(theater_id, date):
    """Fetch showtimes for a specific theater and date."""
    formatted_date = date.strftime("%m-%d-%y").lstrip("0").replace("-0", "-")
    url = f"{AMC_BASE_URL}/theatres/{theater_id}/showtimes/{formatted_date}"
    response = session.get(url, headers=AMC_HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching showtimes for {theater_id} on {formatted_date}: {response.text}")
        return None


def scrape_amc():
    """Scrape AMC theaters for showtimes."""
    all_theaters = get_all_theaters()
    theater_map = {
        t["id"]: t["longName"]
        for t in all_theaters if haversine(SEATTLE_LAT, SEATTLE_LON, t["location"]["latitude"], t["location"]["longitude"]) <= RADIUS_MILES
    }

    for day_offset in range(DAYS_AHEAD + 1):
        show_date = datetime.today() + timedelta(days=day_offset)
        print(f"Fetching AMC showtimes for {show_date.strftime('%m/%d/%Y')}...")

        for theater_id, theater_name in theater_map.items():
            showtimes = get_showtimes(theater_id, show_date)
            if showtimes and "_embedded" in showtimes:
                for showtime in showtimes["_embedded"].get("showtimes", []):
                    dt = datetime.fromisoformat(showtime["showDateTimeLocal"])
                    showtimes_data.append([dt.strftime("%m/%d/%Y"), dt.strftime("%I:%M%p").lstrip("0"), theater_name, showtime["movieName"], showtime.get("runTime", "Unknown"), showtime.get("isAlmostSoldOut"), showtime.get("media", {}).get("posterDynamic")])
        time.sleep(5)


### --- Run Scrapers & Save Data --- ###
scrape_beacon()
scrape_siff()
scrape_amc()

csv_filename = "showtimes.csv"
with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
    csv.writer(csv_file).writerows([["Date", "Time", "Theater", "Film", "Runtime", "isAlmostSoldOut", "posterDynamic"]] + showtimes_data)

print(f"Saved {len(showtimes_data)} showtimes to {csv_filename}.")
