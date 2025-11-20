# Embody Dashboard — Linux Setup & systemd Service

This guide explains how to run the Embody Dashboard Python app on a Linux server and install it as a systemd service so it starts on boot.

**Paths in examples:** replace `/opt/embody-dashboard` and `embody` with the actual installation directory and service user you prefer.

---

## Prerequisites

- A Linux server (Ubuntu/Debian/CentOS/RHEL). Examples below assume Debian/Ubuntu.
- Python 3.10+ installed (this project used Python 3.14 during development). Install with your distro package manager or pyenv.
- `git`, `python3-venv` (or `python3-virtualenv`), and `pip` available.

Quick package install (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
```

## Deploy the project

1. Choose an installation directory and clone the repo (or copy files):

```bash
sudo mkdir -p /opt/embody-dashboard
sudo chown $USER:$USER /opt/embody-dashboard
cd /opt/embody-dashboard
git clone https://github.com/Pon-node/Embody-dashboard.git .
```

2. Create a virtual environment and install Python deps.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# If you don't have a requirements.txt, install the two dependencies used:
pip install flask requests
# OR if you create requirements.txt: pip install -r requirements.txt
```

3. (Optional) Create a `.env` file or environment file to hold secrets (do not commit it):

```ini
# /opt/embody-dashboard/.env
ADMIN_TOKEN=5dfc33056f17eef7f440f2b677abaf7a
API_URL=http://3.141.111.200:8081/api/orchestrators
# Other envs you may add: DB_FILE, UPDATE_INTERVAL
```

Notes:
- The example `test_orchestrators.py` reads constants from the file. For production you should modify the script to read sensitive values from environment variables (recommended) or update the `ADMIN_TOKEN`/`API_URL` directly in the script.
- The app writes an SQLite DB file (default `orchestrators.db`) into the project directory. Ensure the service user has write permission.

## Create a system user (recommended)

Create a dedicated user to run the service (optional but recommended):

```bash
sudo useradd -r -s /usr/sbin/nologin embody
sudo mkdir -p /opt/embody-dashboard
sudo chown -R embody:embody /opt/embody-dashboard
```

If you cloned the repo as your user, change ownership as needed:

```bash
sudo chown -R embody:embody /opt/embody-dashboard
```

## systemd service unit

Create a systemd service file at `/etc/systemd/system/embody-dashboard.service` with the following content (update `User`, `Group`, `WorkingDirectory`, and `ExecStart` paths):

```ini
[Unit]
Description=Embody Dashboard service (Flask)
After=network.target

[Service]
Type=simple
User=embody
Group=embody
WorkingDirectory=/opt/embody-dashboard
# If you used a virtualenv at /opt/embody-dashboard/.venv
EnvironmentFile=/opt/embody-dashboard/.env
ExecStart=/opt/embody-dashboard/.venv/bin/python /opt/embody-dashboard/test_orchestrators.py
Restart=on-failure
RestartSec=5s
# Ensure service has enough file descriptors if needed
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Notes:
- If you don't use an environment file, remove the `EnvironmentFile` line and ensure the variables are present in the environment in another way.
- If your script requires `DISPLAY` or other graphical envs, those must be configured separately.

## Enable and start the service

```bash
# reload systemd configs
sudo systemctl daemon-reload
# enable at boot
sudo systemctl enable embody-dashboard.service
# start now
sudo systemctl start embody-dashboard.service
# check status
sudo systemctl status embody-dashboard.service
# view logs
sudo journalctl -u embody-dashboard.service -f
```

## Common tweaks / troubleshooting

- Permissions: make sure the service user (`embody`) can read the project files and write `orchestrators.db`.
- Python executable path: confirm the path to the venv Python is `/opt/embody-dashboard/.venv/bin/python`. If different, update `ExecStart`.
- If the app must bind to port 80/443, either use a reverse proxy (recommended) or run with appropriate privileges. It's safer to run behind Nginx and proxy to `localhost:5000`.

## Example Nginx reverse-proxy (optional)

Create an Nginx site file to proxy requests to the Flask dev server on `127.0.0.1:5000` (recommended to use a real WSGI server for production):

```nginx
server {
    listen 80;
    server_name your.domain.example;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

After adding the config, enable and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/your.site /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Running with a production WSGI server (recommended)

The current script runs Flask's builtin server which is not recommended for production. Consider using `gunicorn` or `uvicorn` with a small wrapper. Example with `gunicorn`:

```bash
# install gunicorn
source .venv/bin/activate
pip install gunicorn
# start via systemd ExecStart: /opt/embody-dashboard/.venv/bin/gunicorn -w 3 -b 127.0.0.1:5000 test_orchestrators:app
```

If you run via gunicorn, update the `ExecStart` in the systemd unit accordingly.

## Security notes

- Do not commit `ADMIN_TOKEN` or any secrets to git. Use an `EnvironmentFile` and keep it readable only by the service user.
- Consider running the app behind HTTPS using Nginx + Let's Encrypt.

## Backup and data retention

- SQLite DB file (`orchestrators.db`) contains snapshot history. Back it up or rotate as appropriate.
- The script cleans up records older than 25 hours by default. Adjust cleanup policy as needed.

---

If you want, I can:
- Add a `requirements.txt` to the repo (`flask\nrequests`),
- Create the `embody-dashboard.service` unit file in the repo as an example, and
- Update `test_orchestrators.py` to read `ADMIN_TOKEN` and `API_URL` from environment variables.

Tell me which of these you'd like next and I'll add them.
