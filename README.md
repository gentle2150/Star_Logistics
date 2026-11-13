# Star Logistics — starter package tracking website

A Flask + SQLite starter site with:
- Customer tracking lookup
- Shipment status and event history
- Admin login
- Admin shipment creation and status updates
- A clearly marked placeholder for a future official FedEx API connection

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Set environment variables before running. At minimum, change the admin password and secret key.

   Linux/macOS:
   ```bash
   export ADMIN_PASSWORD='choose-a-strong-password'
   export SECRET_KEY='use-a-long-random-secret'
   ```

   Windows PowerShell:
   ```powershell
   $env:ADMIN_PASSWORD='choose-a-strong-password'
   $env:SECRET_KEY='use-a-long-random-secret'
   ```

6. Start the app:

   ```bash
   python app.py
   ```

7. Open http://127.0.0.1:5000

## Demo

Sample tracking number: `STAR123456789`

Admin page: http://127.0.0.1:5000/admin/login

The default development password is `change-me` only if you did not set `ADMIN_PASSWORD`. Change it before use.

## FedEx integration

The FedEx option in the admin form is not a working live integration yet. The `fedex_track()` function is a safe placeholder. To enable real tracking, register through the official FedEx Developer Portal, obtain the appropriate API credentials, implement the current official Track API request and response mapping, and store credentials as server-side environment variables. Never put API secrets in HTML, JavaScript, or a public repository.

This project is not an official FedEx website and does not imply FedEx endorsement. Use FedEx trademarks only with appropriate authorization.

## Before production

- Replace the development secret and admin password.
- Use HTTPS.
- Turn off Flask debug mode.
- Add proper user accounts, password hashing, rate limiting, CSRF protection, backups and audit logging.
- Use a production WSGI server and managed database.
- Implement and test the official courier API integration.
