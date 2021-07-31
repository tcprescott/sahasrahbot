from config import Config as c
from . import core, alttpr, ff1r, smb3r, smz3, z1r, smr, z2r, smwhacks

if c.DEBUG:
    from . import sm as test # this is for the "test" category in my dev RT.gg
