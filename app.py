from flask import Flask, render_template, request, jsonify
import requests
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from datetime import datetime
from env import *

app = Flask(__name__)

# In-memory cache and session
CACHE = {}
CACHE_TTL = 3600  # Cache TTL in seconds (1 hour)
api_key_index = 0
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3/search'

# Prioritized Channels
PRIORITY_CHANNELS = [
    "Gohar Khan",
    "Shobhit Nirwan - 9th",
    "Shobhit Nirwan",
    "Maths By Shobhit Nirwan",
    "ExpHub - Prashant Kirad",
    "Just Padhle"
]
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# API Key Management

# API Key Management
def get_api_key():
    global api_key_index
    if api_key_index >= len(YOUTUBE_API_KEYS):
        print("All API keys exhausted.")
        return None
    return YOUTUBE_API_KEYS[api_key_index]

def switch_to_next_key():
    global api_key_index
    api_key_index += 1
    if api_key_index >= len(YOUTUBE_API_KEYS):
        print("No more API keys left to switch to.")
        return None
    print(f"Switching to next API key: {api_key_index}")
    return get_api_key()


# Format Views
def format_views(views):
    try:
        views = int(views)
        if views >= 1_000_000_000:
            return f"{views / 1_000_000_000:.1f}B"
        elif views >= 1_000_000:
            return f"{views / 1_000_000:.1f}M"
        elif views >= 1_000:
            return f"{views / 1_000:.1f}K"
        return str(views)
    except:
        return "0"

# Get Video Details
@lru_cache(maxsize=1000)
def get_video_details(video_id):
    api_key = get_api_key()
    if not api_key:
        return 0, "N/A", "N/A"
    url = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails,statistics,snippet&id={video_id}&key={api_key}'
    response = session.get(url).json()

    if 'error' in response:
        api_key = switch_to_next_key()
        return 0, "N/A", "N/A"

    try:
        item = response['items'][0]
        duration = item['contentDetails']['duration']
        match = re.match(r'PT((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?', duration)
        h, m, s = int(match.group('hours') or 0), int(match.group('minutes') or 0), int(match.group('seconds') or 0)
        total_duration = h * 3600 + m * 60 + s

        views = format_views(item['statistics'].get('viewCount', 0))
        published_date = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %Y")

        return total_duration, views, published_date
    except:
        return 0, "N/A", "N/A"

# Get Channel Logo
@lru_cache(maxsize=1000)
def get_channel_logo(channel_id):
    api_key = get_api_key()
    if not api_key:
        return None
    url = f'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={api_key}'
    response = session.get(url).json()
    try:
        return response['items'][0]['snippet']['thumbnails']['default']['url']
    except:
        return None

# Fetch Videos
# Fetch Videos
def fetch_videos(query, max_total=100):
    videos = []
    next_page_token = ''
    while len(videos) < max_total and next_page_token is not None:
        api_key = get_api_key()
        if not api_key:
            print("No API key available. Stopping video fetching.")
            break
        
        params = {
            'part': 'snippet',
            'q': f'{query}',
            'type': 'video',
            'key': api_key,
            'maxResults': 50,
            'pageToken': next_page_token
        }

        response = session.get(YOUTUBE_API_URL, params=params).json()

        # Check for API quota exceeded or error
        if 'error' in response:
            print(f"Error: {response['error']['message']}")
            api_key = switch_to_next_key()
            if not api_key:
                break
            continue
        
        new_videos = response.get('items', [])
        next_page_token = response.get('nextPageToken')

        with ThreadPoolExecutor(max_workers=10) as executor:
            details = list(executor.map(lambda v: get_video_details(v['id']['videoId']), new_videos))

        for video, (duration, views, published_date) in zip(new_videos, details):
            if duration >= 180:
                channel_title = video['snippet']['channelTitle']
                channel_logo = get_channel_logo(video['snippet']['channelId'])
                video.update({
                    'duration': duration,
                    'views': views,
                    'published_date': published_date,
                    'channel_logo': channel_logo,
                    'videoId': video['id']['videoId'],
                    'priority': 1 if channel_title in PRIORITY_CHANNELS else 0
                })
                videos.append(video)

    # Sort videos by priority first (1 = prioritized, 0 = regular)
    videos.sort(key=lambda x: x['priority'], reverse=True)

    print(f"Total videos fetched: {len(videos)}")
    return videos

# Routes
@app.route('/')
def home():
    videos = fetch_videos('study motivation')
    return render_template('index.html', videos=videos)

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    videos = fetch_videos(query)
    return render_template('index.html', videos=videos)

@app.route('/play/<video_id>')
def play_video(video_id):
    return render_template('player.html', video_id=video_id)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
