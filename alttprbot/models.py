# coding: utf-8
from sqlalchemy import Column, DateTime, Index, JSON, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import BIGINT, BIT, INTEGER, TINYINT, VARCHAR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class AuditGeneratedGame(Base):
    __tablename__ = 'audit_generated_games'

    id = Column(INTEGER(11), primary_key=True)
    randomizer = Column(String(45))
    hash_id = Column(String(50), index=True)
    permalink = Column(String(2000))
    settings = Column(JSON)
    gentype = Column(String(45))
    genoption = Column(String(45))
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    customizer = Column(INTEGER(11))


class AuditMessage(Base):
    __tablename__ = 'audit_messages'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20))
    message_id = Column(BIGINT(20), index=True)
    user_id = Column(BIGINT(20))
    channel_id = Column(BIGINT(20))
    message_date = Column(DateTime)
    content = Column(String(4000, 'utf8mb4_bin'))
    attachment = Column(String(2000, 'utf8mb4_bin'))
    deleted = Column(INTEGER(11), server_default=text("'0'"))


class Config(Base):
    __tablename__ = 'config'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    parameter = Column(String(45, 'utf8mb4_unicode_ci'), nullable=False)
    value = Column(String(45, 'utf8mb4_unicode_ci'))


class Daily(Base):
    __tablename__ = 'daily'

    id = Column(INTEGER(11), primary_key=True)
    hash = Column(String(45, 'utf8_bin'), nullable=False)


class GtbkGame(Base):
    __tablename__ = 'gtbk_games'

    game_id = Column(INTEGER(11), primary_key=True)
    channel = Column(String(200))
    status = Column(String(45))
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))


class GtbkGuess(Base):
    __tablename__ = 'gtbk_guesses'
    __table_args__ = (
        Index('guess_UNIQUE', 'game_id', 'twitch_user', unique=True),
    )

    guess_id = Column(INTEGER(11), primary_key=True)
    game_id = Column(INTEGER(11))
    twitch_user = Column(String(200))
    guess = Column(INTEGER(11))
    score = Column(INTEGER(11), server_default=text("'0'"))
    timestamp = Column(TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


class GtbkWhitelist(Base):
    __tablename__ = 'gtbk_whitelist'

    id = Column(INTEGER(11), primary_key=True)
    channel = Column(String(200, 'utf8_bin'))
    twitch_user = Column(String(200, 'utf8_bin'))


class MentionCounter(Base):
    __tablename__ = 'mention_counters'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    role_id = Column(BIGINT(20), nullable=False, unique=True)
    counter = Column(INTEGER(11), nullable=False, server_default=text("'1'"))
    last_used = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))


class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    role_id = Column(BIGINT(20), nullable=False)
    permission = Column(String(45, 'utf8mb4_unicode_ci'))


class ReactionGroup(Base):
    __tablename__ = 'reaction_group'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    channel_id = Column(BIGINT(20), nullable=False)
    message_id = Column(BIGINT(20), nullable=False, unique=True)
    name = Column(String(400, 'utf8mb4_unicode_ci'))
    description = Column(VARCHAR(1000))
    bot_managed = Column(INTEGER(11))


class ReactionRole(Base):
    __tablename__ = 'reaction_role'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    reaction_group_id = Column(BIGINT(20))
    role_id = Column(BIGINT(20))
    name = Column(String(45, 'utf8mb4_unicode_ci'), nullable=False)
    emoji = Column(VARCHAR(200), nullable=False)
    description = Column(String(400, 'utf8mb4_unicode_ci'))
    protect_mentions = Column(TINYINT(1))


class SeedPreset(Base):
    __tablename__ = 'seed_presets'

    id = Column(INTEGER(11), primary_key=True)
    name = Column(VARCHAR(45), nullable=False, unique=True)
    randomizer = Column(VARCHAR(45))
    customizer = Column(TINYINT(4))
    settings = Column(JSON, nullable=False)


class SpoilerRace(Base):
    __tablename__ = 'spoiler_races'

    id = Column(INTEGER(11), primary_key=True)
    srl_id = Column(String(45, 'utf8_bin'), nullable=False, unique=True)
    spoiler_url = Column(String(255, 'utf8_bin'), nullable=False)
    studytime = Column(INTEGER(11))
    date = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class SrlNickVerification(Base):
    __tablename__ = 'srl_nick_verification'

    srl_nick = Column(String(45, 'utf8_bin'), primary_key=True, unique=True)
    key = Column(BIGINT(20), unique=True)
    discord_user_id = Column(BIGINT(20))
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))


class SrlRace(Base):
    __tablename__ = 'srl_races'

    id = Column(INTEGER(11), primary_key=True)
    srl_id = Column(String(45), nullable=False, unique=True)
    goal = Column(String(200), nullable=False)
    timestamp = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    message = Column(String(200))


class Srlnick(Base):
    __tablename__ = 'srlnick'

    discord_user_id = Column(BIGINT(20), primary_key=True)
    srl_nick = Column(String(200), index=True)
    twitch_name = Column(String(200), index=True)
    srl_verified = Column(BIT(1))


class TournamentResult(Base):
    __tablename__ = 'tournament_results'

    id = Column(INTEGER(11), primary_key=True)
    srl_id = Column(String(45, 'utf8_bin'))
    episode_id = Column(String(45, 'utf8_bin'))
    permalink = Column(String(200, 'utf8_bin'))
    spoiler = Column(String(200, 'utf8_bin'))
    event = Column(String(45, 'utf8_bin'))
    status = Column(String(45, 'utf8_bin'))
    results_json = Column(JSON)
    week = Column(String(45, 'utf8_bin'))
    written_to_gsheet = Column(TINYINT(4))


class TwitchChannel(Base):
    __tablename__ = 'twitch_channels'

    channel = Column(String(200), primary_key=True)
    group = Column(String(45), nullable=False)


class TwitchCommandText(Base):
    __tablename__ = 'twitch_command_text'
    __table_args__ = (
        Index('idx_twitch_command_text_channel_command', 'channel', 'command', unique=True),
    )

    id = Column(INTEGER(11), primary_key=True)
    channel = Column(String(200, 'utf8_bin'))
    command = Column(String(45, 'utf8_bin'))
    content = Column(String(200, 'utf8_bin'))


class VoiceRole(Base):
    __tablename__ = 'voice_role'

    id = Column(INTEGER(11), primary_key=True)
    guild_id = Column(BIGINT(20), nullable=False)
    voice_channel_id = Column(BIGINT(20), nullable=False)
    role_id = Column(BIGINT(20), nullable=False)
