# GCGN Question of the Week poster

Posts the next Question of the Week to the Gulf Coast Game Nights Facebook Page and Instagram every Monday at 12 PM Eastern. No 30-day scheduling limit: the job runs weekly and posts whatever is next in `queue.csv`.

## How it works

- `queue.csv` is the schedule. The job posts the first row with `status = ready`, then marks it `posted` and commits.
- `captions/<num>.txt` is the caption. `images/<num>.jpg` is the graphic. Same number = same post.
- Mark a row `hold` to skip it. Mark it `ready` again later to put it back in line.
- Add new questions by adding a caption file, an image, and a row at the bottom.

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

### 4. Add the images

Export pages 6 through 21 from the Canva design as JPG and save them as `images/6.jpg` through `images/21.jpg`. Commit and push.

### 5. Test

Repo > Actions > Post Question of the Week > Run workflow. Tick `dry_run`. That posts #6 to the Facebook Page as unpublished (visible in Planner, not in the feed) and skips Instagram. Check it in Meta Business Suite, then delete it there. If it looked right, you are done. The next Monday at noon it posts #6 for real.

## Weekly routine

Nothing. Check the Page on Monday afternoon if you want. When the queue gets to the last two or three `ready` rows, make more.

## Forcing a specific post

Actions > Run workflow > put the number in `only_num`. Useful if you skipped a week and want to catch up.
