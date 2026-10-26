#!/usr/bin/env python3
"""
Posts the next 'ready' Question of the Week to the Gulf Coast Game Nights
Facebook Page and Instagram account, then marks it posted in queue.csv.

Queue columns: num, slug, status, posted_on, fb_post_id, ig_post_id
Captions live in captions/<num>.txt. Images live in images/<num>.jpg.

Env vars (GitHub secrets):
  META_PAGE_TOKEN   long-lived Page access token
  META_PAGE_ID      Facebook Page ID
  META_IG_USER_ID   Instagram business account ID (optional; skip IG if unset)
  IMAGE_BASE_URL    public URL prefix where images/<num>.jpg is reachable
  DRY_RUN           "1" = post to Facebook as unpublished, skip Instagram
"""
import csv, os, sys, time, datetime, urllib.request, urllib.parse, json

GRAPH = "https://graph.facebook.com/v21.0"
QUEUE = "queue.csv"
FIELDS = ["num", "slug", "status", "posted_on", "fb_post_id", "ig_post_id"]


def api(path, data=None, method="POST"):
    url = f"{GRAPH}/{path}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        raise SystemExit(f"Graph API error on {path}: {e.code} {err}")


def read_queue():
    with open(QUEUE, newline="") as f:
        return list(csv.DictReader(f))


def write_queue(rows):
    with open(QUEUE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    token = os.environ["META_PAGE_TOKEN"]
    page_id = os.environ["META_PAGE_ID"]
    ig_id = os.environ.get("META_IG_USER_ID", "").strip()
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    dry = os.environ.get("DRY_RUN", "0") == "1"
    only = os.environ.get("ONLY_NUM", "").strip()  # force a specific row

    rows = read_queue()
    if only:
        pick = next((r for r in rows if r["num"] == only), None)
    else:
        pick = next((r for r in rows if r["status"] == "ready"), None)
    if not pick:
        print("Nothing marked ready in queue.csv. Exiting.")
        return

    num = pick["num"]
    caption = open(f"captions/{num}.txt", encoding="utf-8").read().strip()
    image_url = f"{base}/images/{num}.jpg"
    print(f"Posting #{num} ({pick['slug']}) from {image_url}")
    if dry:
        print("DRY RUN: Facebook post will be unpublished, Instagram skipped.")

    # Facebook Page photo post
    fb = api(f"{page_id}/photos", {
        "url": image_url,
        "message": caption,
        "published": "false" if dry else "true",
        "access_token": token,
    })
    fb_id = fb.get("post_id") or fb.get("id")
    print(f"Facebook: {fb_id}")

    # Instagram: create container, wait for it, publish
    ig_post_id = ""
    if ig_id and not dry:
        c = api(f"{ig_id}/media", {
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        })
        cid = c["id"]
        for _ in range(20):
            st = api(f"{cid}?fields=status_code&access_token={token}", method="GET")
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") == "ERROR":
                raise SystemExit(f"Instagram container failed: {st}")
            time.sleep(3)
        pub = api(f"{ig_id}/media_publish", {
            "creation_id": cid,
            "access_token": token,
        })
        ig_post_id = pub["id"]
        print(f"Instagram: {ig_post_id}")

    if not dry:
        pick["status"] = "posted"
        pick["posted_on"] = datetime.date.today().isoformat()
        pick["fb_post_id"] = fb_id or ""
        pick["ig_post_id"] = ig_post_id
        write_queue(rows)
        print(f"Marked #{num} posted.")


if __name__ == "__main__":
    main()
