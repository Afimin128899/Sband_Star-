import asyncpg
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

async def connect_db():
    return await asyncpg.create_pool(DATABASE_URL)

async def init_db(pool):
    await pool.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        referrer_id BIGINT,
        referrals_count INT DEFAULT 0,
        balance INT DEFAULT 0,
        referral_reward_given BOOLEAN DEFAULT FALSE,
        is_banned BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    await pool.execute("""
    CREATE TABLE IF NOT EXISTS withdrawals (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount INT,
        status TEXT DEFAULT 'pending'
    );
    """)

    await pool.execute("""
    CREATE TABLE IF NOT EXISTS weekly_reset (
        id INT PRIMARY KEY DEFAULT 1,
        last_reset DATE
    );
    """)
