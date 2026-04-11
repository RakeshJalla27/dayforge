# Deployment Steps — Raspberry Pi

Everything needed to go from a fresh Raspberry Pi to a fully running DayForge instance accessible from any device on your home network.

---

## What you need

- Raspberry Pi 4 or 5 (4GB RAM recommended)
- MicroSD card (32GB+) or USB SSD
- Power supply
- Connected to your home network (ethernet or WiFi)
- Your GitHub repo: https://github.com/RakeshJalla27/dayforge

---

## Step 1 — Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Mac
2. Choose **Raspberry Pi OS Lite (64-bit)** — no desktop needed, saves resources
3. Before flashing, click the gear icon (⚙️) in Imager and configure:
   - Hostname: `dayforge`
   - Enable SSH: yes
   - Username/password: set your own
   - WiFi: add your home network credentials
4. Flash to SD card, insert into Pi, power on

---

## Step 2 — SSH into the Pi

From your Mac:

```bash
ssh <your-username>@dayforge.local
```

Wait a minute after first boot for the Pi to finish setup before connecting.

---

## Step 3 — Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for the group change to take effect
exit
```

SSH back in, then verify:

```bash
docker run --rm hello-world
```

---

## Step 4 — Clone the repo

```bash
git clone https://github.com/RakeshJalla27/dayforge.git
cd dayforge
```

---

## Step 5 — Configure environment

```bash
cp .env.example .env
nano .env
```

Set these values:

```dotenv
DB_PASSWORD=choose_a_strong_password
ANTHROPIC_API_KEY=sk-ant-...    # optional — only needed for Plan My Week
PORT=8765
```

Save and exit (`Ctrl+X → Y → Enter`).

---

## Step 6 — Start the app

```bash
docker compose up -d
```

This will:
- Pull `postgres:16-alpine` and build the app image (takes a few minutes on first run)
- Start the database
- Run all migrations automatically
- Create the default Rakesh profile
- Start serving on port 8765

Check it's running:

```bash
docker compose logs -f app
```

You should see:
```
  DayForge Life Planner
  Server       → http://localhost:8765
  Database     → db:5432/dayforge
  Anthropic    → ✓ found
  Press Ctrl+C to stop
```

---

## Step 7 — Import your existing data

If you have existing data (habits, schedule, learning sessions) from your Mac, import it now.

**On your Mac**, copy the data folder to the Pi:

```bash
scp -r data/ <your-username>@dayforge.local:~/dayforge/data/
```

**Then on the Pi**, run the import:

```bash
cd ~/dayforge

docker compose run --rm \
  -e DATABASE_URL=postgresql://dayforge:${DB_PASSWORD}@db:5432/dayforge \
  app python db/import_json.py
```

---

## Step 8 — Verify from your Mac

Open your browser and go to:

```
http://dayforge.local:8765
```

You should see DayForge with all your data intact.

> If `dayforge.local` doesn't resolve, use the Pi's IP address instead.
> Find it with: `ssh <user>@dayforge.local "hostname -I"`

---

## Step 9 — Reserve a static IP (recommended)

Log into your home router and assign a fixed IP to the Pi so it never changes.

1. Find your router's admin page (usually `192.168.1.1` or `192.168.0.1`)
2. Go to DHCP reservations / static leases
3. Find the Pi by hostname `dayforge` or its MAC address
4. Assign a fixed IP e.g. `192.168.1.100`

After this, both of these always work from any device on your network:
- `http://dayforge.local:8765`
- `http://192.168.1.100:8765`

---

## Auto-start on boot

Docker's `restart: unless-stopped` policy in `compose.yml` handles this automatically. The app comes back up after every reboot with no extra configuration.

To verify after a reboot:

```bash
docker compose ps
```

---

## Deploying updates

Whenever you push changes from your Mac, deploy to the Pi with one command:

**On the Pi:**
```bash
cd ~/dayforge
bash deploy.sh
```

This pulls the latest code from GitHub and rebuilds the app container. The database is untouched — only the app restarts.

Or do it remotely from your Mac without SSHing in:

```bash
ssh <your-username>@dayforge.local "cd ~/dayforge && bash deploy.sh"
```

---

## Useful commands on the Pi

```bash
# View live app logs
docker compose logs -f app

# View database logs
docker compose logs -f db

# Restart just the app (after code changes)
docker compose up -d --build app

# Stop everything
docker compose down

# Check container status
docker compose ps

# Backup the database
docker compose exec db pg_dump -U dayforge dayforge > backup_$(date +%F).sql

# Restore from backup
docker compose exec -T db psql -U dayforge dayforge < backup_2026-04-11.sql
```

---

## Development workflow (Mac → Pi)

```
Mac                              Pi
───                              ──
Edit code                        
uv run python server.py  ← test locally
git commit && git push
                          →  bash deploy.sh
                             (git pull + docker rebuild)
                             http://dayforge.local:8765
```

Data on the Pi and data on your Mac are completely separate. The Pi is always the live instance.

---

## Touchscreen notes

The app is touch-optimised for a 10-inch monitor:
- No tap delay (`touch-action: manipulation`)
- Hover states suppressed on touch devices
- Minimum tap target sizes on small buttons and habit calendar cells
- On-screen keyboard works for schedule editing

The Pi browser (Chromium) handles all interactions natively — no extra configuration needed for touch.

---

## TODO

- [ ] Set up HTTPS with a self-signed cert or local CA (optional, for peace of mind on home network)
- [ ] Set up automated daily database backups (cron job on Pi)
- [ ] Cloud deployment to AWS once Pi setup is stable
