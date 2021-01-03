import datetime
import email.utils
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

CACHE_TTL = 10*60
YDL_OPTS = {
    'format': 'worstaudio/worst',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '96',
    }],
    'outtmpl': 'data/%(id)s.%(ext)s',
}

def fetch(url):
    if not hasattr(fetch, 'threads'):
        fetch.threads = {}

    def t():
        logging.info(f'Downloading {url}...')

        with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
            ydl.extract_info(url, download=True)

        logging.info(f'Finished {url}')

    if url not in fetch.threads:
        fetch.threads[url] = threading.Thread(target = t)
        fetch.threads[url].start()

def format_date(date):
    return email.utils.format_datetime(datetime.datetime(year=int(date[0:4]), month=int(date[4:6]), day=int(date[6:8])))

@app.route('/')
def home():
    return 'ok'

@app.route('/podcast.xml')
def podcast():
    if not hasattr(podcast, 'cache'):
        podcast.cache = {}

    url = flask.request.args['url']

    # Spawn a download thread
    fetch(url)

    # Get the info to generate the feed xml
    # Cache automatically
    if url in podcast.cache and podcast.cache['url'][0] >= time.time():
        logging.info(f'Loaded {url} info from cache')
        info = podcast.cache[url]
    else:
        logging.info(f'Not cached: {url}, fetching')
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
            podcast.cache[url] = (time.time() + CACHE_TTL, info)
   
    # Generate the XML
    return flask.Response(
        flask.render_template('podcast.xml', url = url, info = info, format_date = format_date),
        mimetype='application/atom+xml'
    )

@app.route('/<id>.mp3')
def episode(id):
    url = f'https://www.youtube.com/watch?v={id}'

    # If the file already exists, just send it
    mp3_filename = f'data/{id}.mp3'
    if os.path.exists(mp3_filename):
        return flask.send_file(mp3_filename)

    # Otherwise, start a download thread, start a redirect loop on the client
    fetch(url)
    time.sleep(30)
    return flask.redirect(flask.request.url)

if __name__ == '__main__':
    app.run(host = '0.0.0.0')
