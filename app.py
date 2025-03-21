from flask import Flask, render_template, request, jsonify
import requests
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from env import *

app = Flask(__name__)

# In-memory cache to reduce API calls
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


def get_api_key():
    global api_key_index
    if api_key_index >= len(YOUTUBE_API_KEYS):
        print("All API keys have been exhausted.")
        return None
    return YOUTUBE_API_KEYS[api_key_index]


def switch_to_next_key():
    global api_key_index
    api_key_index += 1
    if api_key_index >= len(YOUTUBE_API_KEYS):
        print("All API keys have been exhausted.")


@lru_cache(maxsize=1000)
def get_video_duration(video_id):
    api_key = get_api_key()
    if not api_key:
        return 0
    details_url = f'https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={api_key}'
    details_response = session.get(details_url).json()
    if 'error' in details_response:
        error_message = details_response['error']['message']
        print(f"Error fetching duration: {error_message}")
        if "quota" in error_message.lower():
            switch_to_next_key()
        return 0
    try:
        duration = details_response['items'][0]['contentDetails']['duration']
        match = re.match(r'PT((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?', duration)
        h = int(match.group('hours') or 0)
        m = int(match.group('minutes') or 0)
        s = int(match.group('seconds') or 0)
        return h * 3600 + m * 60 + s
    except (KeyError, IndexError, TypeError):
        return 0


def fetch_videos(query, max_total=100):
    cache_key = f"videos:{query}"
    cached_result = CACHE.get(cache_key)
    if cached_result and time.time() - cached_result['timestamp'] < CACHE_TTL:
        print("Returning cached videos.")
        return cached_result['videos']

    videos = []
    next_page_token = ''

    while len(videos) < max_total and next_page_token is not None:
        api_key = get_api_key()
        if not api_key:
            break
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'videoCategoryId': '27',
            'key': api_key,
            'maxResults': 50,
            'pageToken': next_page_token
        }
        response = session.get(YOUTUBE_API_URL, params=params)
        data = response.json()

        if 'error' in data:
            print(f"Error fetching videos: {data['error']['message']}")
            if "quota" in data['error']['message'].lower():
                switch_to_next_key()
                continue
            break

        next_page_token = data.get('nextPageToken')
        new_videos = data.get('items', [])

        if not new_videos:
            print("No videos found.")
            break

        # Fetch durations concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            durations = list(executor.map(lambda video: get_video_duration(video['id']['videoId']), new_videos))

        priority_videos = []
        filtered_videos = []

        for video, duration_in_seconds in zip(new_videos, durations):
            if duration_in_seconds >= 180:
                channel_title = video['snippet']['channelTitle']
                video['duration'] = duration_in_seconds
                video['videoId'] = video['id']['videoId']
                if channel_title in PRIORITY_CHANNELS:
                    priority_videos.append(video)
                else:
                    filtered_videos.append(video)

        videos.extend(priority_videos + filtered_videos)

    CACHE[cache_key] = {'videos': videos, 'timestamp': time.time()}
    return videos


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
    app.run(debug=True)
