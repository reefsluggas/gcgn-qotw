# GCGN auto-poster

Posts to the Gulf Coast Game Nights Facebook Page and Instagram on a schedule, from GitHub, with no 30-day limit. Runs every hour; whatever is due and hasn't posted yet goes out. Late runs catch up, repeats are blocked.

## What posts when (Eastern)

| Slot | Day | Time | What |
|---|---|---|---|
| burgr-bingo-tomorrow | Sun | 12:00 | Bingo flyer (tournament flyer every other week until Dec 10), "tomorrow night" caption |
| burgr-bingo-tonight | Mon | 10:00 | Bingo flyer, "tonight" caption |
| qotw | Mon | 12:00 | Next Question of the Week from queue.csv |
| burgr-gameshow-tomorrow | Wed | 12:00 | Gameshow flyer (tournament flyer every other week until Dec 10), "tomorrow night" caption |
| burgr-gameshow-tonight | Thu | 10:00 | Gameshow flyer, "tonight" caption |

All of it is in `schedule.csv`. Change a time, a day, or add a row there.

## Burg'r Bar posts

- Captions cycle through `burgr/bingo/captions/{tomorrow,tonight}/*.txt` and `burgr/gameshow/captions/{tomorrow,tonight}/*.txt`, in number order. Add a file to add a caption. A first line of `until: 2026-12-10` makes a caption expire.
- Flyers are in `burgr/flyers/`. In `schedule.csv` the `images` column lists them separated by `;`, with an optional `@2026-12-10` expiry.
- **Photos from the night:** drop JPGs into `burgr/bingo/photos/` or `burgr/gameshow/photos/`. Once there is at least one, posts alternate flyer, photo, flyer, photo, newest photo first. Nothing else to change.
- Posts go out from GCGN with Burg'r Bar named in the caption. The API can't add a collaborator tag, so Walt shares them to his Page if he wants them there.

## Question of the Week

`queue.csv` is the order. The qotw slot posts the first row marked `ready`, then marks it `posted`. Captions in `captions/<num>.txt`, images in `images/<num>.jpg`. Add rows at the bottom when the queue runs low. Mark a row `hold` to skip it.

## Log

`log.csv` records every post: slot, date, image, caption, Facebook and Instagram IDs. The bot commits it after each run.

## Running it by hand

Actions > GCGN auto-poster > Run workflow.
- `dry_run` posts to Facebook as unpublished and skips Instagram. Nothing is logged.
- `only_slot` forces one slot right now, e.g. `burgr-bingo-tonight`.
- `only_num` with the qotw slot forces a specific queue number.

## One-time setup

### 1. Create a Meta app

1. Go to https://developers.facebook.com/apps and click Create App.
2. Use case: Other. App type: Business. Name it `GCGN Poster`. Finish.
3. Leave it in Development mode. That is enough to post to a Page you admin.

### 2. Get a Page token

1. Open https://developers.facebook.com/tools/explorer
2. Top right, pick the `GCGN Poster` app.
3. Under Permissions, add: `pages_manage_posts`, `pages_read_engagement`, `pages_show_list`, `instagram_basic`, `instagram_content_publish`, `business_management`.
4. Click Generate Access Token, log in, pick the Gulf Coast Game Nights Page and the gulfcoastgamenights Instagram account when asked, allow everything.
5. Copy the token it shows. Call it `SHORT_TOKEN`.
6. From the app dashboard, Settings > Basic, copy the App ID and App Secret.

Run this in Terminal, filling in the three values:

```
curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
```

Copy the `access_token` from the response. Call it `LONG_TOKEN`. Then:

```
curl -s "https://graph.facebook.com/v21.0/me/accounts?fields=id,name,access_token,instagram_business_account&access_token=LONG_TOKEN"
```

In the response find Gulf Coast Game Nights. You need three values from it:

- `id` = `META_PAGE_ID`
- `access_token` = `META_PAGE_TOKEN` (this one does not expire)
- `instagram_business_account.id` = `META_IG_USER_ID`

### 3. Add the secrets to this repo

GitHub repo > Settings > Secrets and variables > Actions > New repository secret. Add all three:

- `META_PAGE_TOKEN`
- `META_PAGE_ID`
- `META_IG_USER_ID`
