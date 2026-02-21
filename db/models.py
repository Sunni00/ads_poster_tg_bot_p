CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    phone VARCHAR(20),
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    full_name VARCHAR(510),
    language_code VARCHAR(10),
    is_bot BOOLEAN DEFAULT FALSE,
    role VARCHAR(20) DEFAULT 'client',  -- client / admin / superadmin
    subscription_until TIMESTAMP WITH TIME ZONE,
    last_ad_at TIMESTAMP WITH TIME ZONE,
    extra_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

CREATE_ADS_TABLE = """
CREATE TABLE IF NOT EXISTS ads (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    media_file_ids JSONB NOT NULL,          -- list of file_ids
    text TEXT,
    status VARCHAR(20) DEFAULT 'pending',   -- pending / approved / rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);
"""

CREATE_BLACKOUT_TABLE = """
CREATE TABLE IF NOT EXISTS blackout_periods (
    id SERIAL PRIMARY KEY,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

ALL_TABLES = [CREATE_USERS_TABLE, CREATE_ADS_TABLE, CREATE_BLACKOUT_TABLE]