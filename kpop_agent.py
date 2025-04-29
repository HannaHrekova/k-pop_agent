import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def get_kpop_releases(limit=10):
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    if not API_KEY:
        return "API key is missing. Please set the YOUTUBE_API_KEY environment variable."

    url = "https://www.googleapis.com/youtube/v3/search"
    one_week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"

    params = {
        "part": "snippet",
        "q": "K-pop MV",
        "type": "video",
        "maxResults": limit,
        "order": "date",
        "publishedAfter": one_week_ago,
        "videoCategoryId": "10",
        "key": API_KEY,
    }

    official_kpop_channels = [
        "HYBE LABELS", "JYP Entertainment", "SMTOWN", "YG Entertainment",
        "STAYC Official", "KQ ENTERTAINMENT", "PLEDIS Entertainment",
        "RBW Official", "SOURCE MUSIC", "CUBE Entertainment", "BANGTANTV",
        "BLACKPINK", "officialpsy", "1theK Originals"
    ]

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "items" not in data:
            return "Unable to get new K-pop releases."

        releases = []
        for item in data["items"]:
            video_id = item["id"].get("videoId")
            if not video_id:
                continue 

            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={video_id}"

            if channel in official_kpop_channels and "reaction" not in title.lower():
                releases.append(f"{title} → {link}")
            if len(releases) >= limit:
                break

        return "\n".join(releases) if releases else "There are no new official releases."
    except requests.exceptions.RequestException as e:
        return f"HTTP Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
