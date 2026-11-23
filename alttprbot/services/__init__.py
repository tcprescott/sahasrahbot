"""Domain services: the rules of each feature, shared by every front end.

A service takes IDs, models and plain values, enforces the feature's rules, writes
to the database, and returns models or dataclasses. It never imports an
``alttprbot_*`` package and never builds Discord, racetime or web responses; the
cog, handler or route that calls it does that.
"""
