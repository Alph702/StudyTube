from flask import Flask, render_template, request, jsonify
import re
import asyncio
import aiohttp
from functools import lru_cache
from datetime import datetime
from env import *

app = Flask(__name__)

cache = {}
CACHE_TTL = 3600
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

# API Key Management
def get_api_key():
    global api_key_index
    if api_key_index >= len(YOUTUBE_API_KEYS):
        return None
    return YOUTUBE_API_KEYS[api_key_index]

def switch_to_next_key():
    global api_key_index
    api_key_index += 1
    if api_key_index >= len(YOUTUBE_API_KEYS):
        return None
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

# Extract Duration from ISO 8601
def parse_duration(duration):
    match = re.match(r'PT((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?', duration)
    h, m, s = int(match.group('hours') or 0), int(match.group('minutes') or 0), int(match.group('seconds') or 0)
    return h * 3600 + m * 60 + s

# Fetch Video Details and Channel Logos Concurrently
async def fetch_video_details_and_logo(session, video_id, channel_id, api_key):
    video_url = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails,statistics,snippet&id={video_id}&key={api_key}'
    channel_url = f'https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={api_key}'

    async with session.get(video_url) as video_resp, session.get(channel_url) as channel_resp:
        try:
            video_data = await video_resp.json()
            channel_data = await channel_resp.json()

            # Extract Video Details
            item = video_data['items'][0]
            duration = parse_duration(item['contentDetails']['duration'])
            views = format_views(item['statistics'].get('viewCount', 0))
            published_date = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %Y")
            channel_logo = channel_data['items'][0]['snippet']['thumbnails']['default']['url']

            return duration, views, published_date, channel_logo
        except:
            return 0, "N/A", "N/A", None

async def get_from_cache(key):
    """Retrieve from cache if valid"""
    cached = cache.get(key)
    if cached:
        data, timestamp = cached
        if (datetime.now() - timestamp).total_seconds() < CACHE_TTL:
            print("Serving from cache 🚀")
            return data
    return None

async def set_cache(key, data):
    """Store data in cache with timestamp"""
    cache[key] = (data, datetime.now())

async def fetch_videos(query, max_total=100):
    # Check cache first
    cached_data = await get_from_cache(query)
    if cached_data:
        return cached_data

    videos = []
    next_page_token = ''
    api_key = get_api_key()

    async with aiohttp.ClientSession() as session:
        while len(videos) < max_total and next_page_token is not None:
            if not api_key:
                break

            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'key': api_key,
                'maxResults': 50,
                'pageToken': next_page_token
            }
            async with session.get(YOUTUBE_API_URL, params=params) as response:
                data = await response.json()

                # API Quota Exceeded
                if 'error' in data:
                    api_key = switch_to_next_key()
                    if not api_key:
                        break
                    continue

                new_videos = data.get('items', [])
                next_page_token = data.get('nextPageToken')

                tasks = [
                    fetch_video_details_and_logo(session, v['id']['videoId'], v['snippet']['channelId'], api_key)
                    for v in new_videos
                ]
                details = await asyncio.gather(*tasks)

                for video, (duration, views, published_date, channel_logo) in zip(new_videos, details):
                    if duration >= 180:
                        channel_title = video['snippet']['channelTitle']
                        video.update({
                            'duration': duration,
                            'views': views,
                            'published_date': published_date,
                            'channel_logo': channel_logo,
                            'videoId': video['id']['videoId'],
                            'priority': 1 if channel_title in PRIORITY_CHANNELS else 0
                        })
                        videos.append(video)

        # Sort videos by priority (1 = prioritized, 0 = regular)
        videos.sort(key=lambda x: x['priority'], reverse=True)

        # Cache the result before returning
        await set_cache(query, videos)
        return videos

# Routes
@app.route('/')
def home():
    # Render the loading template first
    return render_template('loading.html')

@app.route('/load_videos', methods=['GET'])
async def load_videos():
    # Simulate data loading
    videos = await fetch_videos('study motivation')
    return render_template('index.html', videos=videos)

@app.route('/search', methods=['POST'])
async def search():
    query = request.form['query']
    videos = await fetch_videos(query)
    return render_template('index.html', videos=videos)

@app.route('/play/<video_id>')
def play_video(video_id):
    return render_template('player.html', video_id=video_id)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
