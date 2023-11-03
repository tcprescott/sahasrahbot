import config

with open('.env', 'r') as env_file:
    lines = env_file.readlines()


with open('config.py', 'a') as settings_file:
    for line in lines:
        if line.startswith('#'):
            continue
        if not line.strip():
            continue
        key, value = line.split('=', maxsplit=1)
        key = key.strip()
        value = value.strip()

        if key == 'DEBUG':
            continue

        if key == 'gsheet_api_oauth':
            continue

        if key == 'SGAPIENDPOINT':
            continue

        settings_file.write(f'\n{key.upper()} = {value}')