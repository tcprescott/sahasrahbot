import random
import urllib.parse

def roll_ffr(url):
    seed = ('%008x' % random.randrange(16**8)).upper()
    up = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(up.query)
    qs['s'] = seed
    newurl = urllib.parse.urlunparse((up.scheme, up.netloc, up.path, up.params,
                                      urllib.parse.urlencode(qs, doseq=True), up.fragment))
    return seed, newurl
