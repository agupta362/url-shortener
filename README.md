# URL Shortener

A full-stack URL shortener to learn on backend systems and DevOps. You can register, shorten links, pick custom codes, and see click analytics. The infrastructure is fully provisioned with Terraform so the whole thing can be torn down and recreated from scratch in a few minutes.

Built over approximately 6 weeks learning backend and DevOps fundamentals.

**Live API (when server is running):** `http://<ec2-ip>:8002/docs` or when running locally: `http://localhost:8002/docs`

> The AWS server isn't kept running 24/7 — I stop it between sessions to stay on the free tier. The Terraform setup means spinning it back up takes one command. See the Terraform section below.

---

## What It Does

- Register and log in with real JWT auth — passwords are hashed with bcrypt before being stored, never plain text
- Get back an access token (30 min) and a refresh token (7 days) — the frontend silently refreshes your session without making you log in again
- Shorten any URL, pick your own custom code or let it generate a random 6-character one
- Every click is logged with a timestamp — real analytics, not just a counter
- Redirects are cached in Redis for 1 hour, so a popular link doesn't hammer Postgres on every single click
- Login is rate limited — 5 wrong attempts per email per 60 seconds and you get a 429. Stops brute-force password guessing before it even reaches the database.
- You only ever see your own links

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Cache / Rate Limiting | Redis |
| Auth | bcrypt (passwords), python-jose (JWT) |
| Frontend | React, Vite |
| Containers | Docker, Docker Compose |
| Cloud | AWS EC2 |
| Infrastructure as Code | Terraform |
| Secrets | AWS SSM Parameter Store |
| IAM | AWS IAM Role (least privilege) |
| State Backend | AWS S3 + DynamoDB locking |
| CI/CD | GitHub Actions |

---

## API Routes

| Method | Route | Auth | What it does |
|--------|-------|------|--------------|
| POST | `/register` | No | Create account |
| POST | `/login` | No | Log in, returns access + refresh tokens. Rate limited via Redis. |
| POST | `/refresh` | No | Get a new access token using your refresh token |
| POST | `/urls` | Yes | Create a short URL |
| GET | `/urls` | Yes | Get all your links with click counts |
| GET | `/{short_code}` | No | Redirect. Served from Redis cache if available. Logs the click either way. |

---

## How the Auth Works

On register, the password goes through bcrypt, only the hash is stored. On login, I hash what was typed and compare it to the stored hash. If it matches, you get two tokens: a short-lived access token for API requests, and a longer refresh token the frontend uses to get a new access token silently when the first one expires. You never have to log in again until the refresh token itself expires after 7 days.

## How Rate Limiting Works

Every login attempt is tracked in Redis under a key tied to that specific email — `login_attempts:someone@email.com`. Redis auto-expires the key after 60 seconds so there's no cleanup code anywhere. Hit 5 attempts in that window and the next request gets blocked with a 429 before the password is even checked, so bcrypt verification never runs on requests that should be rejected anyway.

## How Caching Works

First click on a short link: look it up in Postgres, write the result to Redis with a 1-hour TTL. Every click after that inside that hour reads straight from Redis, no Postgres query. After the hour's up, Redis clears it automatically and the next click starts the cycle again. Click counts still log in Postgres on every request so analytics stay accurate.

---

## Run With Docker (local development)

The easiest way to run this locally. Docker Compose brings up the API, Postgres, and Redis together.

```bash
git clone https://github.com/agupta362/url-shortener.git
cd url-shortener
```

Create a `.env` file in the root:

```env
DB_HOST=db
DB_NAME=urlshortener
DB_USER=postgres
DB_PASSWORD=yourpassword
REDIS_HOST=redis
SECRET_KEY=your_random_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Start the backend:

```bash
docker compose up --build
```

API docs at `http://localhost:8000/docs`

**Then run the frontend** (in a separate terminal):

```bash
cd frontend
```

Open `frontend/src/api.js` and make sure `API_URL` points to your local backend:

```javascript
const API_URL = "http://localhost:8002"
```

Then:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`, register an account, and start shortening links.

---

## Deploy to AWS With Terraform

Everything — EC2 instance, security group, IAM role, SSM parameters — is provisioned by Terraform. Tearing it down and recreating it takes a couple of minutes.

### Prerequisites

- AWS account (free tier is enough)
- Terraform installed (`winget install --id Hashicorp.Terraform --exact` on Windows, `brew install terraform` on Mac)
- AWS CLI configured: `aws configure` with your access key and secret
- An EC2 key pair created in AWS us-east-2. The name doesn't matter — just update `key_name` in `terraform/infra/terraform.tfvars` to match whatever you named it. Download the `.pem` file and keep it, you'll need it to SSH in.

### Why You Need the .pem File

Terraform doesn't SSH into your server. The `.pem` file is your private key — without it, nobody can SSH in, including you. The boot script (user_data) runs automatically inside AWS at first boot, so Terraform doesn't need SSH access for that part, but you'll want the `.pem` if you ever need to get inside the server to debug.

### Folder Structure

```
terraform/
  bootstrap/   ← creates S3 state bucket + DynamoDB lock table (run once, never destroy)
  infra/       ← creates EC2, security group, IAM role, SSM parameters (destroy/apply freely)
```

### First Time Setup (run bootstrap once)

```bash
cd terraform/bootstrap
terraform init
terraform apply
```

This creates the S3 bucket and DynamoDB table that store and lock Terraform's state. You only ever run this once. Never run `terraform destroy` in bootstrap — these need to exist permanently so Terraform can keep track of what it has created.

### Create Your tfvars File

Before running infra, create `terraform/infra/terraform.tfvars` with your own values:

```hcl
aws_region    = "us-east-2"
instance_type = "t3.micro"
key_name      = "your-key-pair-name"
project_name  = "url-shortener"
db_password   = "your_db_password"
secret_key    = "your_jwt_secret_key"
```

This file is in `.gitignore` — you have to create your own and put the values in.

### Deploy the Infrastructure

```bash
cd terraform/infra
terraform init
terraform apply
```

Terraform will:

1. Find the latest Ubuntu 22.04 AMI automatically
2. Create a security group with ports 22, 8000, 8001, 8002 open (I had other projects on 8000/8001 — you can adjust this to just 22 and 8002)
3. Create an IAM role allowing the EC2 instance to read from SSM Parameter Store
4. Store your secrets in SSM as encrypted SecureStrings
5. Launch a t3.micro instance (free tier)
6. Run a boot script that installs Docker, fetches secrets from SSM, clones this repo, creates the `.env` file, and starts the app automatically

When it finishes it prints:

```
public_ip    = "x.x.x.x"
public_dns   = "ec2-x-x-x-x.us-east-2.compute.amazonaws.com"
ssh_command  = "ssh -i ~/.ssh/your-key.pem ubuntu@x.x.x.x"
```

Wait 2-3 minutes for the boot script to finish, then hit `http://<public_ip>:8002/docs`.

**Then update the frontend** to point at the live server. Open `frontend/src/api.js` and change:

```javascript
const API_URL = "http://<your-ec2-ip>:8002"
```

Run `npm run dev` and the frontend connects to the live AWS backend.

### Shut Down (stop free tier usage)

```bash
cd terraform/infra
terraform destroy
```

Tears down EC2, security group, IAM role, and SSM parameters. The S3 bucket and DynamoDB table survive — they're managed by bootstrap, not infra.

### Start Again Next Time

```bash
cd terraform/infra
terraform apply
```

Fresh instance, new IP, secrets fetched from SSM automatically, app running on boot. Update the frontend `API_URL` and the `EC2_HOST` GitHub secret with the new IP.

### What's Stored in SSM Parameter Store

| Parameter | Type | What it is |
|-----------|------|------------|
| `/url-shortener/DB_PASSWORD` | SecureString (encrypted) | Postgres password |
| `/url-shortener/SECRET_KEY` | SecureString (encrypted) | JWT signing key |
| `/url-shortener/DB_NAME` | String | Database name |
| `/url-shortener/DB_USER` | String | Database user |
| `/url-shortener/ALGORITHM` | String | JWT algorithm |
| `/url-shortener/ACCESS_TOKEN_EXPIRE_MINUTES` | String | Token lifetime |
| `/url-shortener/REFRESH_TOKEN_EXPIRE_DAYS` | String | Refresh token lifetime |

SecureString values are encrypted with AWS KMS. The EC2 instance reads them using its IAM role — no credentials stored on the server anywhere.

### State Backend

Terraform state lives in S3, encrypted at rest. DynamoDB prevents two people from running `terraform apply` at the same time by holding a lock for the duration of the operation. If a lock gets stuck after an interrupted apply, clear it with `terraform force-unlock <lock-id>` — the ID is shown in the error message.

---

## CI/CD

Every push to `main` triggers GitHub Actions, which SSHs into the EC2 server and runs `git pull → docker compose down → docker compose up -d --build`. The live API updates automatically on every push.

**To set this up on your own fork:**

Go to your repo → Settings → Secrets and variables → Actions → add these three secrets:

- `EC2_HOST` — your EC2 public IP
- `EC2_USER` — `ubuntu`
- `EC2_KEY` — the full contents of your `.pem` file (open it in a text editor, copy everything including the header and footer lines)

Since the EC2 IP changes every time you stop and restart the instance, update `EC2_HOST` after each restart. A permanent fix is an AWS Elastic IP — free as long as it's attached to a running instance.

---

## Problems I Ran Into and How I Fixed Them

**Wrong AMI ID** — I hardcoded an AMI ID that turned out to be Amazon Linux 2023, not Ubuntu. SSH was failing because I was using `ubuntu@` as the username when Amazon Linux uses `ec2-user`. Fixed by switching to a Terraform `data` source that automatically finds the latest Ubuntu 22.04 AMI — so it never goes stale and you always get the right OS.

**Circular backend dependency** — If you put the S3 bucket and your actual infrastructure in the same Terraform config, `terraform destroy` deletes the bucket that stores the state file. Next `terraform init` fails because the backend is gone. Fixed by splitting into two configs: `bootstrap/` creates the bucket and never gets destroyed, `infra/` creates everything else and can be freely destroyed and recreated.

**State lock not releasing** — An interrupted `terraform apply` left a stale lock in the DynamoDB table. Fixed with `terraform force-unlock <lock-id>`. The lock ID is shown in the error message when you try to run any Terraform command.

**Race condition in boot script** — The EC2 boot script was calling SSM before the IAM role credentials were fully propagated to the instance. Fixed by adding a wait loop: `until aws sts get-caller-identity; do sleep 5; done` before any SSM calls.

---

## What I Learned

**JWT auth** — specifically why you'd have two tokens instead of one. The access token is short-lived so a stolen token expires quickly. The refresh token is long-lived but only ever used to get new access tokens, never for actual API requests. If someone intercepts an access token they have a 30-minute window. If they intercept a refresh token you can revoke it server-side. Two tokens, two different risk profiles.

**Terraform state** — understanding that the state file is Terraform's memory of what it created, and that separating the bucket creation from the rest of the infrastructure is necessary because you can't use a backend that doesn't exist yet. The bootstrap/infra split came after I ran into the problem, understood why it happened, and restructured accordingly.
