# bin Scripts Collection

Personal scripts, tools and helpers in `~/bin`. 381 files, 290 shebang scripts, 48 dedicated shell scripts (below).

## Shell Scripts (48)

| Script | Description |
|--------|-------------|
| `antisocial_scan.sh` | Wi network scanning for ESSID and MAC addresses |
| `antisocial.sh` | Wireless network deauthing/deauth tool |
| `archer_router_wifi_fix_20260923-050642.sh` | Diagnose a "stuck" TP-Link/Archer router: per-interface ping + admin page checks, `wifi` mode for post-reboot Wi-Fi-only verification |
| `banSuckers.sh` | Blocks SSH failed attackers by IP |
| `bbc_ws.sh` | Plays BBC World Service radio stream |
| `bluesound.sh` | PulseAudio loopback for Bluesound speaker |
| `clip-sanitizer.sh` | Sanitizes clipboard contents on change (`clipnotify` loop) |
| `compilerArm.sh` | Links ARM gcc compiler tools |
| `compilerX64.sh` | Removes ARM links for x86 compiler |
| `drop_caches.sh` | Drops system file caches |
| `fantune.sh` | PWM fan control testing and data logging |
| `getTime.sh` | Gets file modification time |
| `git-diff.sh` | Simple git diff using meld |
| `git-meld.sh` | Git repository diff comparison tool |
| `Google.sh` | Google search via elinks browser |
| `h264Parallel.sh` | H264 parallel encoding into segments |
| `icecastFileWebm.sh` | File to WebM streaming via GStreamer |
| `icecast.sh` | Video4linux2 to Icecast Theora/Ogg streaming |
| `icecastWebmIIM.sh` | Video4linux2 to WebM with ICEcast+Jack audio |
| `icecastWebmIIMtest.sh` | Test version with video testsrc |
| `icecastWebm.sh` | Video4linux2 to WebM streaming |
| `icecastWebmX11giss.sh` | X11 screen capture to WebM with GISS |
| `icecastWebmX11IIM.sh` | X11 screen capture to WebM with IIM |
| `icecastWebmX11.sh` | X11 screen capture to WebM |
| `icecastXX.sh` | Xvfb + YouTube effect + WebM streaming |
| `icelocal.sh` | Local video melting and ICE streaming |
| `icemeltFast.sh` | Fast video melting to WebM format |
| `icescreenmelt.sh` | Screen recording melt to WebM |
| `iimTestStream.sh` | Test ICE stream generation |
| `jackgoto.sh` | Jack transport time to seconds conversion |
| `lanDiscover.sh` | LAN discovery using pinger |
| `mailsync.sh` | OfflineIMAP process monitor/killer |
| `manhattanPulse.sh` | Audio streaming to Icecast server |
| `plus.sh` | Cesnet PLUS radio stream player |
| `postFacebook.sh` | Facebook Page photo/text poster (Graph API) |
| `postMastodon.sh` | Mastodon status poster with media |
| `publish.sh` | Publish an image: postgen + Mastodon + Facebook + Ko-fi |
| `radioKlobouk.sh` | Radio streaming to Icecast server |
| `reportIP.sh` | AbuseIPDB IP reputation report |
| `scan.sh` | Wi AP scanner outputting CSV format |
| `screencap.sh` | X11 window capture ffmpeg command generator |
| `screencast.sh` | Screen+Jack audio screencast to MKV |
| `shout.sh` | FIFO-based broadcasting loop |
| `stream.sh` | Icecast MP3 streaming loop |
| `tctosec.sh` | Timecode (HH:MM:SS:FR) to seconds conversion |
| `turbovnc-with-sound.sh` | VNC with sound over SSH tunnel |
| `upyt.sh` | YouTube upload with media info |
| `video_collage.sh` | Video clip collage creator from directory |

## Facebook publishing (postFacebook.sh)

Posts to a Facebook **Page** via the Graph API (personal profiles are not supported by the API).

### One-time token setup (~15 min)
1. `developers.facebook.com` → **Create app** (type: Business) → add **Facebook Login for Business** product.
2. **Graph API Explorer** (in the app) → get a short-lived *user* token with scopes:
   `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `public_profile`.
3. Exchange for a long-lived user token (~60 days):
   `GET https://graph.facebook.com/v25.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={short_token}`
4. Get the Page token + Page ID (long-lived page tokens do not expire unless revoked):
   `GET https://graph.facebook.com/v25.0/me/accounts?access_token={long_lived_user_token}`
   → copy the `id` and `access_token` of your Page.
5. Store them:
   - `echo -n '<PAGE_ACCESS_TOKEN>' > ~/.facebook-token`
   - `echo -n '<PAGE_ID>' > ~/.facebook-page-id`
   (or export `FACEBOOK_TOKEN` / `FACEBOOK_PAGE_ID`).

### Usage
`postFacebook.sh 'caption text' image.png`