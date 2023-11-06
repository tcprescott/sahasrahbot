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
            value = value == 'true'

        if key == 'gsheet_api_oauth':
            continue

        if key == 'SgApiEndpoint':
            key = 'SG_API_ENDPOINT'

        if key == 'RACETIME_SECURE':
            value = value == 'True'

        settings_file.write(f'\n{key.upper()} = {value}')
