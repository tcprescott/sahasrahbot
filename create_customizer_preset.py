import argparse
import json

import yaml
from pyz3r import customizer

parser = argparse.ArgumentParser()
parser.add_argument('customizer_save')
parser.add_argument('preset_name')
parser.add_argument('goal_name')
args = parser.parse_args()
# print(args)

with open(args.customizer_save) as f:
    customizer_settings = json.loads(f.read())

settings = customizer.convert2settings(
    customizer_settings, tournament=True)

data = dict(
    goal_name=args.goal_name,
    customizer=True,
    settings=settings,
)

with open(f'presets/{args.preset_name}.yaml', 'w+') as outfile:
    yaml.dump(data, outfile)
