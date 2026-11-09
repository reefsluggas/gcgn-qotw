#!/usr/bin/env python3
"""
Gulf Coast Game Nights auto-poster.

Runs every hour. For each slot in schedule.csv whose day is today (Eastern)
and whose time has passed, and which has not been posted yet today (log.csv),
it posts to the GCGN Facebook Page and Instagram.

Two kinds of slot:
  queue   one-shot items in order (Question of the Week). source = queue.csv,
          captions/<num>.txt, images/<num>.jpg. Marks the row posted.
  rotate  recurring promo (Burg'r Bar). source = a folder of caption files,
          cycled in order; images = flyer paths separated by ';', each with an
          optional @YYYY-MM-DD expiry; photos = a folder of real photos that,
          when non-empty, alternate with the flyers (newest photo first).
          A caption file may start with a line "until: YYYY-MM-DD" to expire.

Env vars (GitHub secrets):
  META_PAGE_TOKEN, META_PAGE_ID, META_IG_USER_ID, IMAGE_BASE_URL
  DRY_RUN=1   post to Facebook unpublished, skip Instagram, don't log
  ONLY_SLOT   force one slot to post now regardless of day/time/log
  ONLY_NUM    with the queue slot, force a specific queue number
"""
import csv, os, sys, time, json, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

GRAPH = "https://graph.facebook.com/v21.0"
ET = ZoneInfo("America/New_York")
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LOG = "log.csv"
LOG_FIELDS = ["slot", "date", "image", "caption", "fb_post_id", "ig_post_id"]
QUEUE_FIELDS = ["num", "slug", "status", "posted_on", "fb_post_id", "ig_post_id"]


def api(path, data=None, method="POST"):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(f"{GRAPH}/{path}", data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Graph API error on {path}: {e.code} {e.read().decode()}")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def not_expired(expiry, today):
    return not expiry or today <= datetime.date.fromisoformat(expiry)


def publish(image_rel, caption, env, dry):
    """Post one image+caption to FB (and IG unless dry). Returns (fb_id, ig_id)."""
    url = f"{env['base']}/{image_rel}"
    print(f"  image: {url}")
    fb = api(f"{env['page_id']}/photos", {
        "url": url, "message": caption,
        "published": "false" if dry else "true",
        "access_token": env["token"],
    })
    fb_id = fb.get("post_id") or fb.get("id", "")
    print(f"  facebook: {fb_id}")
    ig_id = ""
    if env["ig_id"] and not dry:
        c = api(f"{env['ig_id']}/media", {
            "image_url": url, "caption": caption, "access_token": env["token"],
        })
        for _ in range(20):
            st = api(f"{c['id']}?fields=status_code&access_token={env['token']}", method="GET")
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") == "ERROR":
                raise SystemExit(f"Instagram container failed: {st}")
            time.sleep(3)
        ig_id = api(f"{env['ig_id']}/media_publish", {
            "creation_id": c["id"], "access_token": env["token"],
        })["id"]
        print(f"  instagram: {ig_id}")
    return fb_id, ig_id


def run_queue(slot, env, dry, today, only_num):
    rows = read_csv(slot["source"])
    pick = (next((r for r in rows if r["num"] == only_num), None) if only_num
            else next((r for r in rows if r["status"] == "ready"), None))
    if not pick:
        print("  queue empty, nothing to post")
        return None
    num = pick["num"]
    caption = open(f"captions/{num}.txt", encoding="utf-8").read().strip()
    image = f"images/{num}.jpg"
    print(f"  queue item #{num} ({pick['slug']})")
    fb_id, ig_id = publish(image, caption, env, dry)
    if not dry:
        pick.update(status="posted", posted_on=today.isoformat(), fb_post_id=fb_id, ig_post_id=ig_id)
        write_csv(slot["source"], rows, QUEUE_FIELDS)
    return image, f"captions/{num}.txt", fb_id, ig_id


def run_rotate(slot, env, dry, today, log):
    # how many times this slot has posted before -> drives rotation
    prior = [r for r in log if r["slot"] == slot["slot"]]
    n = len(prior)

    # captions: all files in folder, sorted numerically, minus expired
    cdir = slot["source"]
    caps = []
    for fn in sorted(os.listdir(cdir), key=lambda s: int(os.path.splitext(s)[0]) if s[:-4].isdigit() else 999):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(cdir, fn), encoding="utf-8").read()
        expiry = ""
        if text.startswith("until:"):
            first, text = text.split("\n", 1)
            expiry = first.split(":", 1)[1].strip()
        if not_expired(expiry, today):
            caps.append((os.path.join(cdir, fn), text.strip()))
    if not caps:
        raise SystemExit(f"no usable captions in {cdir}")
    cap_path, caption = caps[n % len(caps)]

    # images: flyers (with expiry) and photos (newest first)
    flyers = []
    for item in filter(None, slot["images"].split(";")):
        path, _, expiry = item.partition("@")
        if not_expired(expiry, today):
            flyers.append(path)
    photos = []
    pdir = slot["photos"]
    if pdir and os.path.isdir(pdir):
        photos = sorted(
            (os.path.join(pdir, f) for f in os.listdir(pdir) if f.lower().endswith((".jpg", ".jpeg"))),
            key=os.path.getmtime, reverse=True)
    if photos and (n % 2 == 1 or not flyers):
        image = photos[(n // 2) % len(photos)]
    else:
        image = flyers[(n // (2 if photos else 1)) % len(flyers)]

    print(f"  rotation #{n+1}: {os.path.basename(cap_path)} + {image}")
    fb_id, ig_id = publish(image, caption, env, dry)
    return image, cap_path, fb_id, ig_id


def main():
    env = {
        "token": os.environ["META_PAGE_TOKEN"],
        "page_id": os.environ["META_PAGE_ID"],
        "ig_id": os.environ.get("META_IG_USER_ID", "").strip(),
        "base": os.environ["IMAGE_BASE_URL"].rstrip("/"),
    }
    dry = os.environ.get("DRY_RUN", "0") == "1"
    only_slot = os.environ.get("ONLY_SLOT", "").strip()
    only_num = os.environ.get("ONLY_NUM", "").strip()

    now = datetime.datetime.now(ET)
    today = now.date()
    dow = DOW[now.weekday()]
    print(f"Now: {now:%a %Y-%m-%d %H:%M} ET{'  (DRY RUN)' if dry else ''}")

    schedule = read_csv("schedule.csv")
    log = read_csv(LOG) if os.path.exists(LOG) else []
    done_today = {r["slot"] for r in log if r["date"] == today.isoformat()}

    posted = 0
    for slot in schedule:
        name = slot["slot"]
        if only_slot:
            if name != only_slot:
                continue
        else:
            if slot["dow"] != dow:
                continue
            if slot["end_date"] and today > datetime.date.fromisoformat(slot["end_date"]):
                continue
            hh, mm = map(int, slot["time_et"].split(":"))
            if (now.hour, now.minute) < (hh, mm):
                print(f"- {name}: not due until {slot['time_et']}")
                continue
            if name in done_today:
                print(f"- {name}: already posted today")
                continue
        print(f"* {name}: posting")
        if slot["kind"] == "queue":
            result = run_queue(slot, env, dry, today, only_num)
        else:
            result = run_rotate(slot, env, dry, today, log)
        if result and not dry:
            image, cap, fb_id, ig_id = result
            log.append({"slot": name, "date": today.isoformat(), "image": image,
                        "caption": cap, "fb_post_id": fb_id, "ig_post_id": ig_id})
            posted += 1
    if posted:
        write_csv(LOG, log, LOG_FIELDS)
    print(f"Done. {posted} post(s).")


if __name__ == "__main__":
    main()
