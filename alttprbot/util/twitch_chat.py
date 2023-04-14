import asyncio
import settings

HOST = "irc.twitch.tv"
PORT = 6667
NICK = settings.TWITCH_USERNAME
PASS = settings.TWITCH_OAUTH_TOKEN

async def get_users(channel):
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
        writer.write(f"PASS {PASS}\n".encode("utf-8"))
        writer.write(f"NICK {NICK}\n".encode("utf-8"))
        writer.write(f"JOIN #{channel}\n".encode("utf-8"))
        writer.write("NAMES\n".encode("utf-8"))
        response = await reader.read(1024)
        users = response.decode("utf-8").split(":")[2].split()
    finally:
        writer.close()
        await writer.wait_closed()

    return users

users = asyncio.run(get_users())
print(users)