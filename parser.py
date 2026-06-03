import asyncio
import json
import sys
import os
import urllib.parse
from collections import defaultdict, deque
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UserPrivacyRestrictedError
from dotenv import load_dotenv
load_dotenv()


API_ID       = os.getenv("API_ID")
API_HASH     = os.getenv("API_HASH")
SESSION_NAME = "gift_session"

# Global state
visited   = set()
visited_names = set()
graph     = defaultdict(list)
user_map  = {}
errors    = []

def log(depth, msg, is_error=False):
    indent = "  " * depth
    formatted_msg = f"{indent}{msg}"
    print(formatted_msg, flush=True)
    if is_error:
        errors.append(msg)

def format_username(user):
    if user is None:
        return "unknown"
    if getattr(user, 'username', None):
        return f"{user.username}"
    name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
    if name:
        return f"{name} (id:{user.id})"
    return f"id:{user.id}"


async def get_gifts(client, entity, depth, delay):
    results = []
    offset  = ""

    try:
        input_user = await client.get_input_entity(entity)
    except Exception as e:
        log(depth, f"⚠️  Could not get input entity for {entity}: {e}", is_error=True)
        return results

    log(depth, f"   🔍 Requesting gifts...")

    page = 0
    while True:
        try:
            await asyncio.sleep(delay)
            response = await client(functions.payments.GetSavedStarGiftsRequest(
                peer    = input_user,
                offset  = offset,
                limit   = 100
            ))
        except FloodWaitError as e:
            log(depth, f"⏳ Rate limited — waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds + 1)
            continue
        except Exception as e:
            log(depth, f"⚠️  GetUserStarGifts failed for {entity}: {type(e).__name__}: {e}", is_error=True)
            break

        page += 1
        gift_count = len(response.gifts) if response.gifts else 0
        user_count = len(response.users) if hasattr(response, 'users') and response.users else 0
        log(depth, f"   📦 Page {page}: {gift_count} gifts, {user_count} bundled users")

        if gift_count == 0:
            log(depth, "   ℹ️  No gifts on this page (user has none, all anonymous, or profile private)")
            break


        bundled_users = {}
        if hasattr(response, 'users') and response.users:
            bundled_users = {u.id: u for u in response.users}
            user_map.update({u.id: format_username(u) for u in response.users})

        for gift in response.gifts:
            raw_from    = getattr(gift, 'from_id', None)
            name_hidden = getattr(gift, 'name_hidden', False)

            if name_hidden or raw_from is None:
                log(depth, f"      ↳ gift skipped (anonymous sender)")
                continue


            from_id = raw_from.user_id if hasattr(raw_from, 'user_id') else raw_from

            sender = bundled_users.get(from_id)
            log(depth, f"      ↳ gift from id:{from_id} ({format_username(sender)})")
            results.append((from_id, sender, gift))

        if getattr(response, 'next_offset', None):
            offset = response.next_offset
        else:
            break

    return results

async def bfs(client, start_username, max_depth, max_users, delay):
    queue = deque([(start_username, 0)])

    while queue and len(visited) < max_users:
        username, depth = queue.popleft()
        
        if depth >= max_depth:
            continue

        log(depth, f"🔎 Resolving '{username}'...")

        try:
            entity = await client.get_entity(username)
        except (UsernameNotOccupiedError, ValueError):
            log(depth, f"❌ User '{username}' not found", is_error=True)
            continue
        except UserPrivacyRestrictedError:
            log(depth, f"🔒 '{username}' is private", is_error=True)
            continue
        except FloodWaitError as e:
            log(depth, f"⏳ Rate limited — waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds + 1)
            queue.appendleft((username, depth)) # retry this user
            continue
        except Exception as e:
            log(depth, f"⚠️  Could not resolve '{username}': {type(e).__name__}: {e}", is_error=True)
            continue

        if entity.id in visited:
            log(depth, f"↩️  Already visited {format_username(entity)}, skipping")
            continue

        visited.add(entity.id)
        display = format_username(entity)
        user_map[entity.id] = display # Ensure consistency for gifters mapping
        visited_names.add(display)

        log(depth, f"👤 Scanning {display} (depth={depth}, visited={len(visited)}/{max_users})")

        gifts = await get_gifts(client, entity, depth, delay)
        log(depth, f"   ✅ {len(gifts)} non-anonymous gifts found")

        gifters = []
        for sender_id, sender_user, gift in gifts:
            sender_display = user_map.get(sender_id) or f"id:{sender_id}"

            graph[sender_display].append({
                "to"      : display,
                "gift_id" : gift.gift.id if getattr(gift, 'gift', None) else None,
                "date"    : gift.date,
                "stars"   : getattr(gift, 'convert_stars', None),
            })

            log(depth, f"   ↳ {sender_display} ──gifted──► {display}")

            # Collect all gifters for frontend, regardless of visited status or username
            gifters.append(sender_display)

            if sender_id not in visited and len(visited) < max_users:
                # Add to queue for further scanning
                next_handle = (sender_user.username if sender_user and sender_user.username else sender_id)
                
                # Only add to queue if depth is within limits
                if depth + 1 < max_depth:
                    queue.append((next_handle, depth + 1))
        yield {'user' : display, 'handle': str(username), 'gifters': list(set(gifters))}
    if len(visited) >= max_users:
        log(0, f"🛑 Reached MAX_USERS ({max_users}), stopping")
    elif not queue:
        log(0, f"🏁 Queue empty, traversal finished")


def print_tree():
    print("\n" + "═" * 50, flush=True)
    print("  GIFT CONNECTION GRAPH", flush=True)
    print("═" * 50, flush=True)
    if not graph:
        print("  (no connections found)", flush=True)
        return
    for sender, edges in graph.items():
        print(f"\n{sender}", flush=True)
        for edge in edges:
            stars = f" ({edge['stars']}⭐)" if edge['stars'] else ""
            print(f"  └─ gifted {edge['to']}{stars}", flush=True)

def save_json(filename="gift_graph_output.json"):
    serializable = {}
    for k, v in graph.items():
        serializable[k] = [
            {**e, "date": e["date"].isoformat() if hasattr(e["date"], "isoformat") else str(e["date"])}
            for e in v
        ]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Graph saved to {filename}", flush=True)

def show_results():
    print("\n" + "═" * 50, flush=True)
    print("  FINAL EXPORT", flush=True)
    print("═" * 50, flush=True)
    print_tree()
    save_json()

    total_edges = sum(len(v) for v in graph.values())
    print(f"\n✅ Done — visited {len(visited)} users, found {total_edges} gift connections", flush=True)


async def parse(config: dict = None):
    global visited, visited_names, graph, user_map, errors
    # Reset state for a new parse run
    visited = set()
    visited_names = set()
    graph = defaultdict(list)
    user_map = {}
    errors = []

    if not API_ID or not API_HASH:
        print("❌ Set your API_ID and API_HASH at the top of the script.")
        print("   Get them from https://my.telegram.org")
        return

    if config is None:
        # Fallback to config.json if no config provided
        try:
            with open("config.json", "r") as config_file:
                config = json.load(config_file)
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return

    start_username = config.get('USERNAME', '').replace('@', '')
    max_depth = config.get('MAX_DEPTH', 4)
    max_users = config.get('MAX_USERS', 100)
    delay = config.get('DELAY', 1.0)

    if not start_username:
        print("❌ No username provided.")
        return

    print(f"\n Starting BFS from @{start_username}", flush=True)
    print(f"   Max depth: {max_depth} | Max users: {max_users} | Delay: {delay}s\n", flush=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(
        phone    = lambda: input("Phone number: "),
        password = lambda: input("2FA password (leave blank if none): ") or None,
    )
    async with client:
        async for node in bfs(client, start_username, max_depth, max_users, delay):
            yield node

    show_results()
    yield {"__done": True, "errors": errors, "visited_count": len(visited)}

if __name__ == "__main__" and 0:
    asyncio.run(parse())