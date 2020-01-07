import asyncio
import datetime
import json
import zlib
import random
import string

import aiofiles
from quart import Quart, abort, request, jsonify

from alttprbot.util import http
# from config import Config as c

APP = Quart(__name__)

MULTIWORLDS = {}

@APP.route('/game', methods=['POST'])
async def create_game():
    data = await request.get_json()

    # if not data['auth_token'] == c.BontaMwHostKey:
    #     abort(401)
    
    if not 'multidata_url' in data and not 'token' in data:
        abort(400)

    port = data.get('port', random.randint(30000, 35000))
    if 'token' in data:
        token = data['token']
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

    global MULTIWORLDS

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
        abort(404)

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
        abort(404)

    if not 'msg' in data:
        abort(400)

    proc = MULTIWORLDS[token]['proc']
    proc.stdin.write(bytearray(data['msg'] + "\n", 'utf-8'))
    await proc.stdin.drain()
    return jsonify(success=True)

@APP.route('/game/<string:token_id>', methods=['DELETE'])
async def delete_game(token_id):
    global MULTIWORLDS

    if not token_id in MULTIWORLDS:
        abort(404)

    proc = MULTIWORLDS[token_id]
    del MULTIWORLDS[token_id]
    await proc.terminate()


def random_string(length=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for i in range(length))

def multiworld_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()
    if isinstance(o, asyncio.subprocess.Process):
        return o.pid

if __name__ == '__main__':
    APP.run()
