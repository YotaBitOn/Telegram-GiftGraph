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


with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_ID       = os.getenv("API_ID")
API_HASH     = os.getenv("API_HASH")
SESSION_NAME = "gift_session"

MAX_DEPTH    = config["MAX_DEPTH"]
MAX_USERS    = config["MAX_USERS"]
DELAY        = config["DELAY"]

visited   = set()
visited_names = set()
graph     = defaultdict(list)
user_map  = {}



def log(depth, msg):
    indent = "  " * depth
    print(f"{indent}{msg}", flush=True)

def format_username(user):
    if user is None:
        return "unknown"
    if getattr(user, 'username', None):
        return f"@{user.username}"
    name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
    return name or f"id:{user.id}"


async def get_gifts(client, entity, depth):
    results = []
    offset  = ""


    try:
        input_user = await client.get_input_entity(entity)
    except Exception as e:
        log(depth, f"⚠️  Could not get input entity: {e}")
        return results

    log(depth, f"   🔍 Requesting gifts...")

    page = 0
    while True:
        try:
            await asyncio.sleep(DELAY)
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
            log(depth, f"⚠️  GetUserStarGifts failed: {type(e).__name__}: {e}")
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

async def bfs(client, start_username):
    queue = deque([(start_username, 0)])
    
    # Pre-resolve the start username if possible to get its ID and avoid visiting it twice
    # However, to keep it simple and consistent with how we handle users, we'll resolve inside the loop.
    
    while queue and len(visited) < MAX_USERS:
        username, depth = queue.popleft()
        
        if depth >= MAX_DEPTH:
            continue

        log(depth, f"🔎 Resolving '{username}'...")

        try:
            entity = await client.get_entity(username)
        except UsernameNotOccupiedError:
            log(depth, f"❌ User '{username}' not found")
            continue
        except UserPrivacyRestrictedError:
            log(depth, f"🔒 '{username}' is private")
            continue
        except Exception as e:
            log(depth, f"⚠️  Could not resolve '{username}': {type(e).__name__}: {e}")
            continue

        if entity.id in visited:
            log(depth, f"↩️  Already visited {format_username(entity)}, skipping")
            continue

        visited.add(entity.id)
        display = format_username(entity)
        visited_names.add(display)
        log(depth, f"👤 Scanning {display} (depth={depth}, visited={len(visited)}/{MAX_USERS})")

        gifts = await get_gifts(client, entity, depth)
        log(depth, f"   ✅ {len(gifts)} non-anonymous gifts found")

        # Update recipient's note
        export_node(display)

        for sender_id, sender_user, gift in gifts:
            sender_display = user_map.get(sender_id) or f"id:{sender_id}"

            graph[sender_display].append({
                "to"      : display,
                "gift_id" : gift.gift.id if getattr(gift, 'gift', None) else None,
                "date"    : gift.date,
                "stars"   : getattr(gift, 'convert_stars', None),
            })

            log(depth, f"   ↳ {sender_display} ──gifted──► {display}")

            # Update only recipient note after each connection is added
            # We don't create notes for senders until they are visited
            export_node(display)
            
            # If the sender is already visited, update their note too (to show the 'Gifted to' link)
            if sender_display in visited_names:
                export_node(sender_display)

            if sender_id not in visited and len(visited) < MAX_USERS:
                next_handle = sender_user.username if (sender_user and sender_user.username) else sender_id
                # Only add to queue if depth is within limits
                if depth + 1 < MAX_DEPTH:
                    queue.append((next_handle, depth + 1))

    if len(visited) >= MAX_USERS:
        log(0, f"🛑 Reached MAX_USERS ({MAX_USERS}), stopping")
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

def export_node(node, vault_dir="gift_vault"):
    import os
    os.makedirs(vault_dir, exist_ok=True)

    filename = node.lstrip("@").replace("/", "_").replace(" ", "_") + ".md"
    filepath = os.path.join(vault_dir, filename)

    sections = [f"№ {node}"]

    sent = graph.get(node, [])
    if sent:
        block = ["\n\n### Gifted to"]
        for edge in sent:
            target = edge["to"].lstrip("@")
            stars = f" — {edge['stars']}⭐" if edge["stars"] else ""
            block.append(f"\n- [[{target}]]{stars}")
        sections.append("".join(block))

    received = []
    for sender, edges in graph.items():
        for e in edges:
            if e["to"] == node:
                received.append((sender, e))

    if received:
        block = ["\n\n### Received from"]
        for sender, edge in received:
            src = sender.lstrip("@")
            stars = f" — {edge['stars']}⭐" if edge["stars"] else ""
            block.append(f"\n- [[{src}]]{stars}")
        sections.append("".join(block))

    content = "".join(sections)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    # log(0, f"      📄 Updated note: {filename}")

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


async def parse():
    if not API_ID or not API_HASH:
        print("❌ Set your API_ID and API_HASH at the top of the script.")
        print("   Get them from https://my.telegram.org")
        return

    start_username = config['USERNAME']
    if not start_username:
        print("❌ No username provided.")
        return

    print(f"\n🚀 Starting BFS from @{start_username}", flush=True)
    print(f"   Max depth: {MAX_DEPTH} | Max users: {MAX_USERS} | Delay: {DELAY}s\n", flush=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(
        phone    = lambda: input("Phone number: "),
        password = lambda: input("2FA password (leave blank if none): ") or None,
    )
    async with client:
        await bfs(client, start_username)

    print("\n" + "═" * 50, flush=True)
    print("  FINAL EXPORT", flush=True)
    print("═" * 50, flush=True)
    print_tree()
    save_json()

    total_edges = sum(len(v) for v in graph.values())
    print(f"\n✅ Done — visited {len(visited)} users, found {total_edges} gift connections", flush=True)

if __name__ == "__main__" and 0:
    asyncio.run(parse())