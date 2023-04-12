#!.venv/bin/python
import asyncio
import os
import tempfile
import urllib.parse
from shortuuid import ShortUUID

import boto3
from dotenv import load_dotenv
from pytube import YouTube
from pytube.helpers import RegexMatchError
from pytube.exceptions import VideoUnavailable
from tortoise import Tortoise
from slugify import slugify

import settings
from alttprbot import models

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "sahasrahbot")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = urllib.parse.quote_plus(os.environ.get("DB_PASS", "pass"))


session = boto3.session.Session()
s3 = session.client(
    's3',
    region_name="sfo2",
    endpoint_url="https://sfo2.digitaloceanspaces.com",
    aws_access_key_id=settings.SPACES_KEY,
    aws_secret_access_key=settings.SPACES_SECRET
)

def send_vod_to_s3(player_name: str, youtube_url: str, video_name: str, bucket: str = 'synack'):
    try:
        yt = YouTube(youtube_url)
    except RegexMatchError as e:
        return None

    try:
        stream = yt.streams.filter(res=["144p", "240p", "360p", "480p"], progressive=True).order_by('resolution').desc().first()
    except VideoUnavailable:
        return None

    uuid = ShortUUID().random(length=8)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_name = stream.download(tmpdir)
        file_extension = os.path.splitext(file_name)[1].strip(".")
        key = f'mt2023_vods/{player_name}/{video_name}_{uuid}.{file_extension}'
        s3.upload_file(file_name, bucket, key, ExtraArgs={'ACL': 'public-read'})

    url_safe_key = urllib.parse.quote(key, safe="~()*!.'")
    return f'https://{bucket}.sfo2.digitaloceanspaces.com/{url_safe_key}'

async def database():
    await Tortoise.init(
        db_url=f'mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )

async def main():
    await database()

    undownloaded_races = await models.AsyncTournamentRace.filter(
        runner_vod_s3_uri__isnull=True,
        runner_vod_url__isnull=False,
        status='finished',
        tournament_id=4,
        review_status='accepted',
    ).prefetch_related('tournament', 'user', 'permalink', 'permalink__pool')

    for race in undownloaded_races:
        player_name = slugify(race.user.display_name, max_length=20)
        video_name = slugify(f"{race.permalink.pool.name}_{race.id}", max_length=50)
        print(f"Downloading VoD {player_name}/{video_name}")
        uri = send_vod_to_s3(player_name, race.runner_vod_url, video_name)
        if uri is None:
            print(f"Failed to download video for {race.id}")
            continue
        await race.refresh_from_db()
        race.runner_vod_s3_uri = uri
        await race.save(update_fields=['runner_vod_s3_uri'])

async def test():
    await database()
    player_name = "test"
    video_name = slugify("Test Pool_1234", max_length=50)
    uri = send_vod_to_s3(player_name, 'https://www.youtube.com/watch?v=K-coNtCjY_c', video_name)
    print(uri)

loop = asyncio.get_event_loop()
task = loop.create_task(main())
loop.run_until_complete(task)