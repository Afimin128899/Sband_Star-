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
        balance NUMERIC(10,2) DEFAULT 0,
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
