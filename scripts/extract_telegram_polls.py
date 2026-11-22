import os
import sys
import json
import random
import asyncio
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.functions.messages import SendVoteRequest
from telethon.errors import FloodWaitError

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SESSION_PATH = r"C:\Users\Nikhil-Arun\Documents\antigravity\vibrant-davinci\tg_declutter_session"
ENV_PATH = r"C:\Users\Nikhil-Arun\Documents\antigravity\vibrant-davinci\.env.telegram"
CACHE_PATH = r"c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\science_polls_cache.json"

def load_env():
    env = {}
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("\"'")
    return int(env.get("TG_API_ID") or env.get("TELEGRAM_API_ID") or 0), env.get("TG_API_HASH") or env.get("TELEGRAM_API_HASH") or ""

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
    return {}

def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

async def main():
    api_id, api_hash = load_env()
    client = TelegramClient(SESSION_PATH, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Error: Client not authorized!", flush=True)
        return
        
    channel_id = -1001381225775 # Science By Rahul Deshmukh
    channel = await client.get_entity(channel_id)
    print(f"Connected to channel: {channel.title} (@{getattr(channel, 'username', '')})", flush=True)
    
    cache = load_cache()
    print(f"Loaded {len(cache)} polls from existing cache.", flush=True)
    
    cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    scanned = 0
    poll_count = 0
    new_extracted = 0
    
    print(f"Scanning messages back to {cutoff_date.date()}...", flush=True)
    
    async for msg in client.iter_messages(channel, limit=None):
        scanned += 1
        if msg.date < cutoff_date:
            print(f"Reached cutoff date: {msg.date}. Ending scan.", flush=True)
            break
            
        if not msg.poll or not getattr(msg.poll.poll, 'quiz', False):
            continue
            
        poll_count += 1
        msg_id_str = str(msg.id)
        
        # Check if already processed with correct answer
        if msg_id_str in cache and cache[msg_id_str].get("correct_option_idx") is not None:
            continue
            
        poll = msg.poll.poll
        question_text = poll.question.text if hasattr(poll.question, 'text') else str(poll.question)
        answers = [a.text.text if hasattr(a.text, 'text') else str(a.text) for a in poll.answers]
        options_bytes = [a.option for a in poll.answers]
        
        correct_idx = None
        solution_text = None
        voter_counts = {}
        total_voters = 0
        
        # First check if user already voted and answer is present in message
        if msg.poll.results and getattr(msg.poll.results, 'results', None):
            res_list = msg.poll.results.results
            for idx, opt_bytes in enumerate(options_bytes):
                for r in res_list:
                    if r.option == opt_bytes:
                        voter_counts[idx] = r.voters
                        if r.correct:
                            correct_idx = idx
            total_voters = msg.poll.results.total_voters or 0
            solution_text = getattr(msg.poll.results, 'solution', None)
            
        # If not known, send anonymous dummy vote to unlock official answer
        if correct_idx is None and not poll.closed:
            while True:
                try:
                    vote_res = await client(SendVoteRequest(
                        peer=channel,
                        msg_id=msg.id,
                        options=[options_bytes[0]] # vote first option
                    ))
                    # Parse results
                    for update in getattr(vote_res, 'updates', []):
                        if hasattr(update, 'results'):
                            poll_res = update.results
                            total_voters = poll_res.total_voters or 0
                            solution_text = getattr(poll_res, 'solution', None)
                            for r in getattr(poll_res, 'results', []):
                                for idx, opt_bytes in enumerate(options_bytes):
                                    if r.option == opt_bytes:
                                        voter_counts[idx] = r.voters
                                        if r.correct:
                                            correct_idx = idx
                    new_extracted += 1
                    print(f"[{len(cache)+1}] Extracted Msg {msg.id} ({msg.date.date()}) | Correct Opt: {correct_idx}", flush=True)
                    # Jitter sleep to avoid flood wait
                    await asyncio.sleep(random.uniform(0.35, 0.65))
                    break
                except FloodWaitError as e:
                    print(f"Telegram FloodWaitError: sleeping {e.seconds + 2}s...", flush=True)
                    await asyncio.sleep(e.seconds + 2)
                except Exception as e:
                    print(f"Failed to vote on Msg {msg.id}: {e}", flush=True)
                    break
                    
        # Store in cache
        cache[msg_id_str] = {
            "msg_id": msg.id,
            "date": msg.date.isoformat(),
            "question": question_text.strip(),
            "answers": answers,
            "correct_option_idx": correct_idx,
            "solution": solution_text,
            "total_voters": total_voters,
            "voter_counts": voter_counts
        }
        
        save_cache(cache)
            
    save_cache(cache)
    print(f"\nExtraction Finished! Total 2025-2026 Polls in Cache: {len(cache)}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
