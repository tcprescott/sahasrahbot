import discord
from discord.ext import commands

import asyncio
import string
import random
import os

from config import Config as c

multiworlds = {}

class BontaMultiworld(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if ctx.guild.id in c.BontaMultiworldServers:
            return True
        else:
            return False


    @commands.command()
    async def mwgenerate(self, ctx):
        token = await generate_multiworld()
        port = await start_multiworld(token)

        await ctx.send(
            f'Game ROMs: {c.MultiworldRomBase}/multiworld/{token}\n'
            f'Host: {c.MultiworldHostBase}:{port}'
        )

    @commands.command()
    async def mwresume(self, ctx, token, port):
        port = await start_multiworld(token, port)

        await ctx.send(
            f'Game ROMs: {c.MultiworldRomBase}/multiworld/{token}\n'
            f'Host: {c.MultiworldHostBase}:{port}'
        )

    @commands.command()
    @commands.is_owner()
    async def mwmsg(self, ctx, token, msg):
        await cleanup_procs()
        global multiworlds
        proc = multiworlds[token]
        proc.stdin.write(bytearray(msg + "\n", 'utf-8'))
        await proc.stdin.drain()


    @commands.command()
    async def mwgames(self, ctx):
        await cleanup_procs()
        global multiworlds

        if len(multiworlds) > 0:
            tokens = []
            for token in multiworlds:
                tokens.append(token)
            await ctx.send("\n".join(tokens))

async def cleanup_procs():
    global multiworlds
    for token in multiworlds:
        world_proc = multiworlds[token]
        if world_proc.returncode is not None:
            del multiworlds[token]

async def start_multiworld(token, port=None):
    if port is None:
        port = random.randint(30000,35000)
    path = f'/var/www/html/multiworld/{token}'

    multidata_files = [f for f in os.listdir(path) if f.endswith('_multidata')]

    cmd = [
        '/opt/multiworld/ALttPEntranceRandomizer/env/bin/python',
        '/opt/multiworld/ALttPEntranceRandomizer/MultiServer.py',
        '--port', str(port),
        '--multidata', f'{path}/{multidata_files[0]}'
    ]
    print(' '.join(cmd))
    proc = await asyncio.create_subprocess_shell(
        ' '.join(cmd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE)

    global multiworlds
    multiworlds[token] = proc
    return port
    
async def generate_multiworld():
    rnd_token = randomString(6)
    os.mkdir(f'/var/www/html/multiworld/{rnd_token}')
    cmd = [
        '/opt/multiworld/ALttPEntranceRandomizer/env/bin/python',
        '/opt/multiworld/ALttPEntranceRandomizer/EntranceRandomizer.py',
        '--mode','open',
        '--goal','ganon',
        '--difficulty','normal',
        '--progressive','on',
        '--algorithm','balanced',
        '--shuffle','vanilla',
        '--rom','/opt/multiworld/ROM/Zelda_3_Jap_v1.sfc',
        '--fastmenu','normal',
        '--heartbeep','half',
        '--hints',
        '--heartcolor','red',
        '--skip_playthrough',
        '--multi','2', #player count
        #'--names','Synack,SomeoneElse', #names
        '--outputpath',f'/var/www/html/multiworld/{rnd_token}'
    ]
    print(' '.join(cmd))
    proc = await asyncio.create_subprocess_shell(
        ' '.join(cmd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    
    await proc.wait()
    if proc.returncode > 0:
        raise Exception('Failed to generate multiworld game!')
    else:
        return rnd_token

def randomString(stringLength=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for i in range(stringLength))

def setup(bot):
    bot.add_cog(BontaMultiworld(bot))