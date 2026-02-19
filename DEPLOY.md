# Deploy ClubGPT to Digital Ocean

## Option 1: App Platform (Easiest)

1. **Push to GitHub**
   ```bash
   cd clubgpt
   git init
   git add .
   git commit -m "ClubGPT v0.1"
   gh repo create clubgpt --private --push
   ```

2. **Create App on DO**
   - Go to https://cloud.digitalocean.com/apps
   - Click "Create App"
   - Select your GitHub repo
   - It auto-detects the Dockerfile

3. **Add Environment Variable**
   - In app settings, add:
   - `ANTHROPIC_API_KEY` = your key (mark as secret)

4. **Deploy**
   - Click Deploy
   - Get your URL: `https://clubgpt-xxxxx.ondigitalocean.app`

**Cost:** ~$5/month (Basic XXS)

---

## Option 2: Droplet (More Control)

1. **Create Droplet**
   - Image: Docker on Ubuntu
   - Size: $6/month (1GB RAM)
   - Region: Sydney (closest to Brisbane)

2. **SSH In**
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Clone & Run**
   ```bash
   git clone https://github.com/your-username/clubgpt.git
   cd clubgpt
   
   # Create .env
   echo "ANTHROPIC_API_KEY=sk-ant-xxx" > .env
   
   # Run with Docker
   docker-compose up -d
   ```

4. **Setup Domain (Optional)**
   ```bash
   # Install Caddy for auto-HTTPS
   apt install caddy
   
   # Edit /etc/caddy/Caddyfile
   clubgpt.yourdomain.com {
       reverse_proxy localhost:8000
   }
   
   systemctl restart caddy
   ```

---

## Option 3: One-Click Deploy

Run this on any server with Docker:

```bash
docker run -d \
  --name clubgpt \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-xxx \
  ghcr.io/your-username/clubgpt:latest
```

---

## Security Notes

- Never commit `.env` with real keys
- Use DO's secret management for API keys
- Consider adding auth if public-facing
