"""
Tracker Roblox - suit le statut et le profil de pseudos donnes.
Utilise l'API publique Roblox (users, presence, friends, thumbnails, premium, groups, badges).
"""

__author__ = "@Zuma"

import sys
import time
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.theme import Theme
from rich.rule import Rule
from rich.align import Align

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DARK_THEME = Theme({
    "accent": "bold bright_cyan",
    "accent.dim": "cyan",
    "label": "bold grey70",
    "value": "white",
    "muted": "grey50",
    "ok": "bold bright_green",
    "bad": "bold bright_red",
    "warn": "bold bright_yellow",
    "online": "bold bright_green",
    "offline": "grey50",
    "ingame": "bold spring_green2",
    "studio": "bold turquoise2",
})

console = Console(theme=DARK_THEME)

CONFIG_FILE = "config.json"

PRESENCE_TYPES = {
    0: "Hors ligne",
    1: "En ligne (site)",
    2: "En jeu",
    3: "En Studio",
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {
            "discord_webhook_url": "",
            "discord_bot_token": "",
            "discord_log_channel_id": "",
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def http_request(url, payload=None, method="GET", headers=None, retries=3):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                return resp.status, body
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise urllib.error.URLError("Trop de tentatives (429)")


def http_post_json(url, payload, headers=None):
    return http_request(url, payload=payload, method="POST", headers=headers)


def http_get_json(url, headers=None):
    status, body = http_request(url, method="GET", headers=headers)
    return json.loads(body)


def get_user_ids(usernames):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": usernames, "excludeBannedUsers": False}
    status, body = http_post_json(url, payload)
    data = json.loads(body)
    result = {}
    for entry in data.get("data", []):
        result[entry["requestedUsername"].lower()] = {
            "id": entry["id"],
            "name": entry["name"],
        }
    return result


def resolve_user(query):
    """Accepte un pseudo ou un ID Roblox numerique, renvoie {'id', 'name'} ou None."""
    query = query.strip()
    if query.isdigit():
        details = get_user_details(int(query))
        if details and details.get("id"):
            return {"id": details["id"], "name": details.get("name", query)}
        return None

    users = get_user_ids([query])
    info = users.get(query.lower())
    return info


def get_presences(user_ids):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": user_ids}
    status, body = http_post_json(url, payload)
    data = json.loads(body)
    result = {}
    for entry in data.get("userPresences", []):
        result[entry["userId"]] = entry
    return result


def get_user_details(user_id):
    try:
        return http_get_json(f"https://users.roblox.com/v1/users/{user_id}")
    except (urllib.error.URLError, json.JSONDecodeError):
        return {}


def get_avatar_thumbnail(user_id):
    try:
        data = http_get_json(
            f"https://thumbnails.roblox.com/v1/users/avatar-headshot"
            f"?userIds={user_id}&size=150x150&format=Png&isCircular=false"
        )
        items = data.get("data", [])
        if items:
            return items[0].get("imageUrl")
    except (urllib.error.URLError, json.JSONDecodeError):
        pass
    return None


def get_friends_count(user_id):
    try:
        data = http_get_json(f"https://friends.roblox.com/v1/users/{user_id}/friends/count")
        return data.get("count")
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_friends_names(user_id):
    try:
        data = http_get_json(f"https://friends.roblox.com/v1/users/{user_id}/friends")
        friend_ids = [f["id"] for f in data.get("data", [])]
    except (urllib.error.URLError, json.JSONDecodeError):
        return None

    if not friend_ids:
        return []

    names = []
    batch_size = 100
    for i in range(0, len(friend_ids), batch_size):
        batch = friend_ids[i : i + batch_size]
        try:
            status, body = http_post_json(
                "https://users.roblox.com/v1/users",
                {"userIds": batch, "excludeBannedUsers": False},
            )
            info = json.loads(body)
            names.extend(entry["name"] for entry in info.get("data", []))
        except (urllib.error.URLError, json.JSONDecodeError):
            continue

    return names


def get_followers_count(user_id):
    try:
        data = http_get_json(f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
        return data.get("count")
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_following_count(user_id):
    try:
        data = http_get_json(f"https://friends.roblox.com/v1/users/{user_id}/followings/count")
        return data.get("count")
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_roblox_badges(user_id):
    try:
        data = http_get_json(
            f"https://accountinformation.roblox.com/v1/users/{user_id}/roblox-badges"
        )
        return [b.get("name") for b in data if b.get("name")]
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_groups_count(user_id):
    try:
        data = http_get_json(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        return len(data.get("data", []))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_groups_detail(user_id):
    try:
        data = http_get_json(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        result = []
        for entry in data.get("data", []):
            group_name = entry.get("group", {}).get("name")
            role_name = entry.get("role", {}).get("name")
            rank = entry.get("role", {}).get("rank")
            result.append(f"{group_name} ({role_name}, rang {rank})")
        return result
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_name_history(user_id):
    try:
        data = http_get_json(
            f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=50&sortOrder=Asc"
        )
        return [entry["name"] for entry in data.get("data", [])]
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_created_games(user_id):
    try:
        data = http_get_json(
            f"https://games.roblox.com/v2/users/{user_id}/games?accessFilter=Public&limit=50"
        )
        result = []
        for entry in data.get("data", []):
            name = entry.get("name")
            visits = entry.get("placeVisits")
            result.append(f"{name} ({visits} visites)")
        return result
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_avatar_outfit(user_id):
    try:
        data = http_get_json(f"https://avatar.roblox.com/v1/users/{user_id}/avatar")
        assets = data.get("assets", [])
        return [
            f"{a.get('name')} ({a.get('assetType', {}).get('name')})" for a in assets
        ]
    except (urllib.error.URLError, json.JSONDecodeError):
        return None


def get_premium_status(user_id):
    try:
        status, body = http_request(
            f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership"
        )
        return body.decode("utf-8").strip().lower() == "true"
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None


def format_account_age(created_iso):
    try:
        created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return created_iso, None
    now = datetime.now(timezone.utc)
    days = (now - created).days
    years = days // 365
    remaining_days = days % 365
    if years > 0:
        age_str = f"{years} an(s) et {remaining_days} jour(s)"
    else:
        age_str = f"{days} jour(s)"
    return created.strftime("%Y-%m-%d"), age_str


def describe_presence(presence):
    presence_type = presence.get("userPresenceType", 0)
    status = PRESENCE_TYPES.get(presence_type, "Inconnu")
    place_name = presence.get("lastLocation") or None
    if presence_type == 0:
        place_name = None
    return status, place_name


STATUS_COLORS = {
    "Hors ligne": 0x6B7280,
    "En ligne (site)": 0x22C55E,
    "En jeu": 0x16A34A,
    "En Studio": 0x06B6D4,
    "Inconnu": 0xEAB308,
}


def build_search_embed(profile, status, place_name):
    label = status if not place_name else f"{status} — {place_name}"
    embed = {
        "title": f"Recherche : {profile['name']}",
        "url": f"https://www.roblox.com/users/{profile['id']}/profile",
        "color": STATUS_COLORS.get(status, 0x6B7280),
        "fields": [
            {"name": "Statut", "value": label, "inline": True},
            {"name": "ID Roblox", "value": str(profile["id"]), "inline": True},
            {"name": "Amis", "value": str(profile.get("friends") or "Inconnu"), "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if profile.get("avatar_url"):
        embed["thumbnail"] = {"url": profile["avatar_url"]}
    return embed


def log_search_via_webhook(webhook_url, profile, status, place_name):
    embed = build_search_embed(profile, status, place_name)
    try:
        http_post_json(webhook_url, {"embeds": [embed]})
    except urllib.error.URLError as e:
        console.print(f"[bad]Echec envoi webhook Discord :[/] {e}")


def log_search_via_bot(bot_token, channel_id, profile, status, place_name):
    embed = build_search_embed(profile, status, place_name)
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    try:
        http_post_json(
            url,
            {"embeds": [embed]},
            headers={"Authorization": f"Bot {bot_token}"},
        )
    except urllib.error.URLError as e:
        console.print(f"[bad]Echec envoi via bot Discord :[/] {e}")


def log_search_to_discord(config, profile, status, place_name):
    bot_token = config.get("discord_bot_token", "")
    channel_id = config.get("discord_log_channel_id", "")
    webhook_url = config.get("discord_webhook_url", "")

    if bot_token and channel_id:
        log_search_via_bot(bot_token, channel_id, profile, status, place_name)
    elif webhook_url:
        log_search_via_webhook(webhook_url, profile, status, place_name)


def collect_profile(user_id, name):
    steps = [
        ("Profil de base", lambda: get_user_details(user_id)),
        ("Avatar (visage)", lambda: get_avatar_thumbnail(user_id)),
        ("Nombre d'amis", lambda: get_friends_count(user_id)),
        ("Liste des amis", lambda: get_friends_names(user_id)),
        ("Abonnes", lambda: get_followers_count(user_id)),
        ("Abonnements", lambda: get_following_count(user_id)),
        ("Badges Roblox", lambda: get_roblox_badges(user_id)),
        ("Nombre de groupes", lambda: get_groups_count(user_id)),
        ("Detail des groupes", lambda: get_groups_detail(user_id)),
        ("Statut Premium", lambda: get_premium_status(user_id)),
        ("Historique des pseudos", lambda: get_name_history(user_id)),
        ("Jeux crees", lambda: get_created_games(user_id)),
        ("Tenue de l'avatar", lambda: get_avatar_outfit(user_id)),
    ]

    fields = {}
    details = {}

    progress_columns = (
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, complete_style="cyan", finished_style="green"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )

    with Progress(*progress_columns, console=console, transient=True) as progress:
        task = progress.add_task(f"Recherche de {name}...", total=len(steps))
        for label, func in steps:
            progress.update(task, description=label)
            result = func()
            if label == "Profil de base":
                details = result or {}
            else:
                fields[label] = result
            progress.advance(task)
            time.sleep(0.3)

    created_date, account_age = format_account_age(details.get("created", ""))

    return {
        "id": user_id,
        "name": name,
        "display_name": details.get("displayName"),
        "description": (details.get("description") or "").strip() or None,
        "verified_badge": details.get("hasVerifiedBadge"),
        "banned": details.get("isBanned"),
        "created": created_date,
        "account_age": account_age,
        "avatar_url": fields.get("Avatar (visage)"),
        "friends": fields.get("Nombre d'amis"),
        "friends_names": fields.get("Liste des amis"),
        "followers": fields.get("Abonnes"),
        "following": fields.get("Abonnements"),
        "roblox_badges": fields.get("Badges Roblox"),
        "groups": fields.get("Nombre de groupes"),
        "groups_detail": fields.get("Detail des groupes"),
        "premium": fields.get("Statut Premium"),
        "name_history": fields.get("Historique des pseudos"),
        "created_games": fields.get("Jeux crees"),
        "avatar_outfit": fields.get("Tenue de l'avatar"),
    }


STATUS_STYLES = {
    "Hors ligne": ("offline", "⚫"),
    "En ligne (site)": ("online", "🟢"),
    "En jeu": ("ingame", "🎮"),
    "En Studio": ("studio", "🛠️"),
    "Inconnu": ("warn", "❔"),
}


def yes_no(value, unknown_if_none=True):
    if value is None and unknown_if_none:
        return "[warn]Inconnu[/]"
    return "[ok]Oui[/]" if value else "[bad]Non[/]"


def join_or(items, empty_label="Aucun"):
    if items is None:
        return "[warn]Inconnu[/]"
    if len(items) == 0:
        return f"[muted]{empty_label}[/]"
    return ", ".join(items)


def section(title, style="accent.dim"):
    console.print(Rule(f"[{style}]{title}[/]", style=style, align="left"))


def print_profile(profile, status, place_name):
    style, icon = STATUS_STYLES.get(status, ("value", "❔"))
    label = status if not place_name else f"{status} — {place_name}"

    header = f"[bold white]{profile['name']}[/]"
    if profile.get("display_name") and profile["display_name"] != profile["name"]:
        header += f"  [muted](affiche : {profile['display_name']})[/]"
    header += f"\n[{style}]{icon} {label}[/]"

    console.print()
    console.print(Panel(
        Align.left(header),
        title=f"[accent]ID {profile['id']}[/]",
        border_style=style,
        expand=False,
        padding=(1, 3),
    ))

    info = Table.grid(padding=(0, 3))
    info.add_column(style="label", no_wrap=True)
    info.add_column(style="value")

    info.add_row("Badge verifie", yes_no(profile.get("verified_badge"), unknown_if_none=False))
    info.add_row("Premium", yes_no(profile.get("premium")))
    info.add_row("Banni", yes_no(profile.get("banned"), unknown_if_none=False))
    info.add_row("Compte cree le", profile.get("created") or "[warn]Inconnu[/]")
    info.add_row("Anciennete", profile.get("account_age") or "[warn]Inconnue[/]")
    info.add_row("Amis", str(profile.get("friends")) if profile.get("friends") is not None else "[warn]Inconnu[/]")
    info.add_row("Abonnes (followers)", str(profile.get("followers")) if profile.get("followers") is not None else "[warn]Inconnu[/]")
    info.add_row("Abonnements", str(profile.get("following")) if profile.get("following") is not None else "[warn]Inconnu[/]")
    info.add_row("Groupes", str(profile.get("groups")) if profile.get("groups") is not None else "[warn]Inconnu[/]")
    info.add_row("Badges Roblox", join_or(profile.get("roblox_badges")))
    info.add_row("Avatar (visage)", profile.get("avatar_url") or "[warn]Inconnu[/]")

    console.print(Panel(info, border_style="grey35", padding=(1, 2), expand=False))

    friends_names = profile.get("friends_names")
    if friends_names:
        section(f"AMIS ({len(friends_names)})")
        console.print(Panel(", ".join(friends_names), border_style="grey35", expand=False))

    groups_detail = profile.get("groups_detail")
    if groups_detail:
        section("GROUPES")
        groups_table = Table(show_header=True, header_style="accent", border_style="grey35")
        groups_table.add_column("Groupe")
        groups_table.add_column("Role")
        for g in groups_detail:
            if "(" in g:
                gname, rest = g.rsplit(" (", 1)
                groups_table.add_row(gname, rest.rstrip(")"))
            else:
                groups_table.add_row(g, "")
        console.print(groups_table)

    name_history = profile.get("name_history")
    if name_history:
        section("ANCIENS PSEUDOS")
        console.print(Panel(", ".join(name_history), border_style="grey35", expand=False))

    created_games = profile.get("created_games")
    if created_games:
        section("JEUX CREES")
        console.print(Panel(", ".join(created_games), border_style="grey35", expand=False))

    avatar_outfit = profile.get("avatar_outfit")
    if avatar_outfit:
        section("TENUE DE L'AVATAR")
        console.print(Panel(", ".join(avatar_outfit), border_style="grey35", expand=False))

    if profile.get("description"):
        desc = profile["description"].replace("\n", " ")
        if len(desc) > 300:
            desc = desc[:300] + "..."
        section("BIO")
        console.print(Panel(desc, border_style="grey35", expand=False))

    console.print()


EXPORTS_DIR = "exports"


def safe_filename(name):
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


def export_profile_json(profile, status, place_name):
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filename = f"{safe_filename(profile['name'])}_{time.strftime('%Y-%m-%d_%H%M%S')}.json"
    path = os.path.join(EXPORTS_DIR, filename)
    payload = dict(profile)
    payload["status"] = status
    payload["place"] = place_name
    payload["exported_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def export_profile_txt(profile, status, place_name):
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filename = f"{safe_filename(profile['name'])}_{time.strftime('%Y-%m-%d_%H%M%S')}.txt"
    path = os.path.join(EXPORTS_DIR, filename)

    label = status if not place_name else f"{status} - {place_name}"
    lines = [
        f"===== {profile['name']} (ID: {profile['id']}) =====",
        f"Nom affiche       : {profile.get('display_name') or '-'}",
        f"Statut            : {label}",
        f"Badge verifie     : {'Oui' if profile.get('verified_badge') else 'Non'}",
        f"Premium           : {'Oui' if profile.get('premium') else 'Non' if profile.get('premium') is not None else 'Inconnu'}",
        f"Banni             : {'Oui' if profile.get('banned') else 'Non'}",
        f"Compte cree le    : {profile.get('created') or 'Inconnu'}",
        f"Anciennete        : {profile.get('account_age') or 'Inconnue'}",
        f"Amis              : {profile.get('friends')}",
        f"Liste amis        : {', '.join(profile.get('friends_names') or [])}",
        f"Abonnes           : {profile.get('followers')}",
        f"Abonnements       : {profile.get('following')}",
        f"Badges Roblox     : {', '.join(profile.get('roblox_badges') or [])}",
        f"Groupes           : {profile.get('groups')}",
        f"Liste groupes     : {', '.join(profile.get('groups_detail') or [])}",
        f"Anciens pseudos   : {', '.join(profile.get('name_history') or [])}",
        f"Jeux crees        : {', '.join(profile.get('created_games') or [])}",
        f"Tenue avatar      : {', '.join(profile.get('avatar_outfit') or [])}",
        f"Avatar (visage)   : {profile.get('avatar_url') or 'Inconnu'}",
        f"Bio               : {profile.get('description') or ''}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def export_prompt(profile, status, place_name):
    choice = console.input(
        "[dim]Exporter ce profil ? [json/txt/Entree pour ignorer] :[/] "
    ).strip().lower()
    if choice == "json":
        path = export_profile_json(profile, status, place_name)
        console.print(f"[green]Profil exporte :[/] {path}")
    elif choice == "txt":
        path = export_profile_txt(profile, status, place_name)
        console.print(f"[green]Profil exporte :[/] {path}")


def search_user(query, config=None):
    config = config or {}
    try:
        info = resolve_user(query)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        console.print(f"[red]Erreur recuperation de l'utilisateur:[/] {e}")
        return

    if not info:
        console.print(f"[red]Introuvable (pseudo ou ID) :[/] {query}")
        return

    uid, name = info["id"], info["name"]

    try:
        presences = get_presences([uid])
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        console.print(f"[red]Erreur recuperation de la presence:[/] {e}")
        return

    presence = presences.get(uid)
    status, place_name = describe_presence(presence) if presence else ("Inconnu", None)

    profile = collect_profile(uid, name)
    print_profile(profile, status, place_name)

    log_search_to_discord(config, profile, status, place_name)

    export_prompt(profile, status, place_name)


def main():
    config = load_config()

    console.clear()
    console.print(Panel.fit(
        Align.center(
            "[accent]TRACKER ROBLOX[/]\n[muted]Recherche de profils publics Roblox[/]\n[muted]Cree par @Zuma[/]"
        ),
        border_style="accent.dim",
        padding=(1, 6),
    ))
    console.print(
        "[muted]Entre un [bold]pseudo[/bold] ou un [bold]ID[/bold] Roblox. "
        "Tape [accent]quit[/accent] pour quitter.[/]\n"
    )

    try:
        while True:
            username = console.input("[accent]➤ Rechercher :[/] ").strip()
            if not username:
                continue
            if username.lower() in ("quit", "exit", "q"):
                break
            search_user(username, config)
    except KeyboardInterrupt:
        console.print("\n[muted]Arret du tracker.[/]")


if __name__ == "__main__":
    main()
