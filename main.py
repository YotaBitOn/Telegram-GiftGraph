import asyncio
import json
import sys
import os
from collections import defaultdict
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, UsernameNotOccupiedError, UserPrivacyRestrictedError
from dotenv import load_dotenv
load_dotenv()



API_ID       = os.getenv("API_ID")
API_HASH     = os.getenv("API_HASH")
SESSION_NAME = "gift_session"

MAX_DEPTH    = 6
MAX_USERS    = 100
DELAY        = 2.5

visited   = set()
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
    """Fetch all visible gifts. entity must be the full User object (not just an ID)."""
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

async def dfs(client, username, depth=0):
    if len(visited) >= MAX_USERS:
        log(depth, f"🛑 Reached MAX_USERS ({MAX_USERS}), stopping")
        return
    if depth >= MAX_DEPTH:
        log(depth, f"🛑 Reached MAX_DEPTH ({MAX_DEPTH}), stopping")
        return

    log(depth, f"🔎 Resolving '{username}'...")

    try:
        entity = await client.get_entity(username)
    except UsernameNotOccupiedError:
        log(depth, f"❌ User '{username}' not found")
        return
    except UserPrivacyRestrictedError:
        log(depth, f"🔒 '{username}' is private")
        return
    except Exception as e:
        log(depth, f"⚠️  Could not resolve '{username}': {type(e).__name__}: {e}")
        return

    if entity.id in visited:
        log(depth, f"↩️  Already visited {format_username(entity)}, skipping")
        return

    visited.add(entity.id)
    display = format_username(entity)
    log(depth, f"👤 Scanning {display} (depth={depth}, visited={len(visited)}/{MAX_USERS})")

    gifts = await get_gifts(client, entity, depth)
    log(depth, f"   ✅ {len(gifts)} non-anonymous gifts found")

    for sender_id, sender_user, gift in gifts:
        sender_display = user_map.get(sender_id) or f"id:{sender_id}"

        graph[sender_display].append({
            "to"      : display,
            "gift_id" : gift.gift.id if getattr(gift, 'gift', None) else None,
            "date"    : gift.date,
            "stars"   : getattr(gift, 'convert_stars', None),
        })

        log(depth, f"   ↳ {sender_display} ──gifted──► {display}")

        if sender_id not in visited and len(visited) < MAX_USERS:
            next_handle = sender_user.username if (sender_user and sender_user.username) else sender_id
            await dfs(client, next_handle, depth + 1)



            if sender_id not in visited:
                graph[sender_display].pop()


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

def export_obsidian(vault_dir="gift_vault"):
    import os
    os.makedirs(vault_dir, exist_ok=True)


    all_nodes = set(graph.keys())

    for edges in graph.values():
        for edge in edges:
            all_nodes.add(edge["to"])

    for node in all_nodes:
        filename = node.lstrip("@").replace("/", "_").replace(" ", "_") + ".md"
        filepath = os.path.join(vault_dir, filename)

        sections = [f"№ {node}"]


        sent = graph.get(node, [])
        if sent:
            block = ["Gifted to"]
            for edge in sent:
                target = edge["to"].lstrip("@")
                stars  = f" — {edge['stars']}⭐" if edge["stars"] else ""
                block.append(f"- [[{target}]]{stars}")
            sections.append("".join(block))


        received = [(sender, e) for sender, edges in graph.items() for e in edges if e["to"] == node]
        if received:
            block = ["Received from"]
            for sender, edge in received:
                src   = sender.lstrip("@")
                stars = f" — {edge['stars']}⭐" if edge["stars"] else ""
                block.append(f"- [[{src}]]{stars}")
            sections.append("".join(block))


        content = "".join(sections) + ""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"Obsidian vault saved to '{vault_dir}/' ({len(all_nodes)} notes)", flush=True)
    print(f"   Open it in Obsidian: File → Open Vault → select the folder", flush=True)

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


async def main():
    if not API_ID or not API_HASH:
        print("❌ Set your API_ID and API_HASH at the top of the script.")
        print("   Get them from https://my.telegram.org")
        return

    start_username = input("Enter starting @username (without @): ").strip().lstrip("@")
    if not start_username:
        print("❌ No username provided.")
        return

    print(f"\n🚀 Starting DFS from @{start_username}", flush=True)
    print(f"   Max depth: {MAX_DEPTH} | Max users: {MAX_USERS} | Delay: {DELAY}s\n", flush=True)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(
        phone    = lambda: input("Phone number: "),
        password = lambda: input("2FA password (leave blank if none): ") or None,
    )
    async with client:
        await dfs(client, start_username)

    print_tree()
    save_json()
    export_obsidian()

    total_edges = sum(len(v) for v in graph.values())
    print(f"\n✅ Done — visited {len(visited)} users, found {total_edges} gift connections", flush=True)

if __name__ == "__main__":
    asyncio.run(main())