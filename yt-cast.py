import datetime
import email.utils
import hashlib
import json
import fileinput
import flask
import logging
import threading
import time
import os
import re
import youtube_dl

logging.basicConfig(level = logging.INFO)
os.makedirs('data', exist_ok=True)
app = flask.Flask(__name__)

CUTOFF = {'weeks': 12}
DOWNLOAD_QUEUE = []
CONFIG_FILE = 'config.json'
CACHE_TTL = 6*60*60 # 6 hours
YDL_OPTS = {
    'format': 'worstaudio/worst',
    'keepvideo': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '96',
    }],
    'outtmpl': 'data/%(id)s.%(ext)s',
}

# Initial load config
with open(CONFIG_FILE, 'r') as fin:
    config = json.load(fin)

# Helper function to turn youtube dates into podcast dates
def format_date(date):
    return email.utils.format_datetime(datetime.datetime(year=int(date[0:4]), month=int(date[4:6]), day=int(date[6:8])))

# Get the cache file for a url
def path_for(url):
    hash = hashlib.md5(url.encode()).hexdigest()
    return f'data/{hash}.json'

# When we should return history back to
def cutoff():
    return (datetime.date.today() - datetime.timedelta(**CUTOFF)).strftime('%Y%m%d')

# Download a single youtube video
def download_thread():
    # Prepopulate with any missing videos
    logging.info('Prepopulating download queue')
    for key in config:
        for url in config[key]:
            path = path_for(url)
            if not os.path.exists(path):
                continue

            with open(path, 'r') as fin:
                info = json.load(fin)
                if 'entries' in info:
                    for entry in info['entries']:
                        DOWNLOAD_QUEUE.append(entry['id'])
                else:
                    DOWNLOAD_QUEUE.append(info['id'])

    # Download loop
    while True:
        while DOWNLOAD_QUEUE:
            id = DOWNLOAD_QUEUE.pop()
            logging.info(f'Download queue [{len(DOWNLOAD_QUEUE)}]: {id}')

            url = f'https://www.youtube.com/watch?v={id}'
            logging.info(f'Downloading video at {url}')
            with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
                ydl.extract_info(url, download=True)

        time.sleep(60)

# A thread to download information on the requested URLs periodically
def update_thread():
    # Update once a minute, but caches will probably mostly be used
    while True:
        with open(CONFIG_FILE, 'r') as fin:
            config = json.load(fin)

        for key in config:
            for url in config[key]:
                path = path_for(url)

                # If we don't have the metadata (or an update in the last hour), download it
                if not os.path.exists(path) or os.path.getmtime(path) + CACHE_TTL < time.time():
                    logging.info(f'Fetching {url}')
                    try:
                        with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
                            info = ydl.extract_info(url, download=False)
                            with open(path, 'w') as fout:
                                json.dump(info, fout)

                            # Queue downloads for all videos (existing ones will be skipped)
                            if 'entries' in info:
                                for entry in info['entries']:
                                    if entry['upload_date'] >= cutoff():
                                        DOWNLOAD_QUEUE.append(entry['id'])
                            else:
                                if info['upload_date'] >= cutoff():
                                    DOWNLOAD_QUEUE.append(info['id'])

                    except Exception as ex:
                        logging.error(f'Failed to fetch {url}: {ex}')

        time.sleep(60)

@app.route('/<key>.xml')
def podcast(key):
    entries = []

    for url in config[key]:
        path = path_for(url)
        if not os.path.exists(path):
            continue

        with open(path, 'r') as fin:
            info = json.load(fin)
            if 'entries' in info:
                for entry in info['entries']:
                    if entry['upload_date'] >= cutoff():
                        entries.append(entry)
            else:
                if info['upload_date'] >= cutoff():
                    entries.append(info)

    entries = list(reversed(sorted(entries, key=lambda entry: entry['upload_date'])))

    # Generate the XML
    return flask.Response(
        flask.render_template('podcast.xml', key = key, entries = entries, format_date = format_date),
        mimetype='application/atom+xml'
    )

@app.route('/<id>.mp3')
def episode(id):
    if not re.match(r'^[a-zA-Z0-9_-]+$', id):
        raise Exception('Close but no cigar')

    return flask.send_file(f'data/{id}.mp3')

if __name__ == '__main__':
    threading.Thread(target=download_thread, daemon=True).start()
    threading.Thread(target=update_thread, daemon=True).start()

    app.run(host = '0.0.0.0')
