import asyncio
import datetime
import json
import random
import socket
import string
import zlib

import aiofiles
from quart import Quart, abort, jsonify, request

from alttprbot.util import http

# from config import Config as c

APP = Quart(__name__)

MULTIWORLDS = {}

@APP.route('/game', methods=['POST'])
async def create_game():
    global MULTIWORLDS

    data = await request.get_json()
    
    if not 'multidata_url' in data and not 'token' in data:
        abort(400, description=f'Missing multidata_url or token in data')

    port = int(data.get('port', random.randint(30000, 35000)))

    if port < 30000 or port > 35000:
        abort(400, description=f'Port {port} is out of bounds.')
    if is_port_in_use(port):
        abort(400, description=f'Port {port} is in use!')

    if 'token' in data:
        token = data['token']
        if token in MULTIWORLDS:
            abort(400, description=f'Game with token {token} already exists.')
    else:
        binary = await http.request_generic(data['multidata_url'], method='get', returntype='binary')
        json.loads(zlib.decompress(binary).decode("utf-8"))
        
        token = random_string(6)

        async with aiofiles.open(f"data/multidata_files/{token}_multidata", "wb") as multidata_file:
            await multidata_file.write(binary)

    cmd = [
        '/opt/multiworld/BontaMultiworld_v31/env/bin/python',
        '/opt/multiworld/BontaMultiworld_v31/MultiServer.py',
        '--port', str(port),
        '--multidata', f"data/multidata_files/{token}_multidata"
    ]

    proc = await asyncio.create_subprocess_shell(
        ' '.join(cmd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE)

    await asyncio.sleep(1)

    if proc.returncode is not None:
        abort(400, 'Multiserver failed to start.')

    MULTIWORLDS[token] = {
        'token': token,
        'proc': proc,
        'port': port,
        'admin': data.get('admin', None),
        'date': datetime.datetime.now(),
        'meta': data.get('meta', None)
    }
    response = APP.response_class(
        response=json.dumps(MULTIWORLDS[token], default=multiworld_converter),
        status=200,
        mimetype='application/json'
    )
    return response

@APP.route('/game', methods=['GET'])
async def get_all_games():
    global MULTIWORLDS
    response = APP.response_class(
        response=json.dumps(MULTIWORLDS, default=multiworld_converter),
        status=200,
        mimetype='application/json'
    )
    return response

@APP.route('/game/<string:token>', methods=['GET'])
async def get_game(token):
    global MULTIWORLDS

    if not token in MULTIWORLDS:
        abort(404, description=f'Game with token {token} was not found.')

    response = APP.response_class(
        response=json.dumps(MULTIWORLDS[token], default=multiworld_converter),
        status=200,
        mimetype='application/json'
    )
    return response

@APP.route('/game/<string:token>/msg', methods=['PUT'])
async def update_game(token):
    data = await request.get_json()

    global MULTIWORLDS

    if not token in MULTIWORLDS:
        abort(404, description=f'Game with token {token} was not found.')

    if not 'msg' in data:
        abort(400)

    proc = MULTIWORLDS[token]['proc']
    proc.stdin.write(bytearray(data['msg'] + "\n", 'utf-8'))
    await proc.stdin.drain()
    return jsonify(success=True)

@APP.route('/game/<string:token>', methods=['DELETE'])
async def delete_game(token):
    global MULTIWORLDS

    if not token in MULTIWORLDS:
        abort(404, description=f'Game with token {token} was not found.')

    close_game(token)
    return jsonify(success=True)

@APP.route('/jobs/cleanup/<int:minutes>', methods=['POST'])
async def cleanup(minutes):
    global MULTIWORLDS
    tokens_to_clean = []
    for token in MULTIWORLDS:
        if MULTIWORLDS[token]['date'] < datetime.datetime.now()-datetime.timedelta(minutes=minutes):
            tokens_to_clean.append(token)
    for token in tokens_to_clean:
        close_game(token)
    return jsonify(success=True, count=len(tokens_to_clean), cleaned_tokens=tokens_to_clean)

@APP.errorhandler(400)
def bad_request(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)

@APP.errorhandler(404)
def game_not_found(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)

@APP.errorhandler(500)
def something_bad_happened(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)

def close_game(token):
    proc = MULTIWORLDS[token]['proc']
    if proc.returncode is None:
        proc.terminate()
    else:
        print(f'process {proc.pid} already terminated')
    del MULTIWORLDS[token]

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('0.0.0.0', port)) == 0

def random_string(length=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for i in range(length))

def multiworld_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()
    if isinstance(o, asyncio.subprocess.Process):
        return o.pid

if __name__ == '__main__':
    APP.run(host='127.0.0.1', port=5000, use_reloader=False)
