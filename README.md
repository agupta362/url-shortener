# URL Shortener

A URL shortener with real auth, caching, rate limiting, and click analytics behind it. You can register, shorten links, pick your own custom codes, and see how many times each link's been clicked. Redirects are cached so repeated clicks don't hit the database every time.

> The AWS server isn't running 24/7 — I stop it between sessions to stay on the free tier, so the IP changes when I restart it. If the live link below is dead, just run it locally with the steps below, or set up your own EC2 instance using the guide at the bottom.

## What it does

- Register and log in with real auth — passwords are hashed with bcrypt, never stored as plain text. You get a short-lived access token and a longer refresh token so you're not logging in every 30 minutes
- Login is rate limited through Redis — 5 wrong passwords in a minute and you're locked out for a bit
- Shorten a link with a custom code or let it generate a random one
- Every click gets logged with a timestamp, so there's real analytics, not just a counter
- Redirects are cached in Redis for an hour, so a popular link isn't hitting Postgres on every single click
- You only see your own links, nobody else's
- Small React frontend on top instead of just the Swagger docs
- Pushing to main auto-deploys the whole thing to AWS through GitHub Actions

## Stack

Python + FastAPI on the backend, PostgreSQL for the data, Redis for caching and rate limiting, bcrypt + python-jose for auth. React + Vite on the frontend. Docker Compose runs all of it together, deployed on an AWS EC2 instance with GitHub Actions handling the deploys.

## Routes

| Method | Route | Needs auth? | What it does |
|--------|-------|----------------|--------------|
| POST | /register | No | Creates an account |
| POST | /login | No | Logs you in, returns access + refresh tokens. Rate limited. |
| POST | /refresh | No | Trade your refresh token for a new access token |
| POST | /urls | Yes | Shorten a new URL |
| GET | /urls | Yes | See your links |
| GET | /{short_code} | No | The actual redirect. Pulls from Redis if cached, otherwise hits Postgres and caches it. |

## How auth works

On register, the password gets run through bcrypt and only the hash is saved. On login, I hash whatever was typed and compare it to the stored hash. If it matches, you get an access token good for 30 minutes and a refresh token good for 7 days. The access token goes on every request after that. Once it expires, the frontend uses the refresh token to quietly grab a new one in the background instead of forcing a re-login.

## How rate limiting works

Every login attempt gets tracked in Redis under a key tied to that email, like `login_attempts:someone@email.com`. Redis can expire keys on its own, so I set it to clear after 60 seconds and never have to clean it up manually. If an email hits 5 attempts inside that window, the next one gets a 429 before the password is even checked — so a bad actor can't make the server run the slow bcrypt comparison over and over either.

## How caching works

First click on a link, it gets looked up in Postgres, then dropped into Redis with a 1-hour expiry. Every click after that, for the next hour, skips Postgres entirely and reads straight from Redis. After the hour's up, the key clears itself and the next click starts the cycle again. Click counts still log in Postgres either way, so the analytics stay accurate regardless of caching.

## Running it locally

**Backend:**

```
git clone https://github.com/agupta362/url-shortener.git
cd url-shortener
```

Create a `.env` file in the root:
```
DB_HOST=db
DB_NAME=urlshortener
DB_USER=postgres
DB_PASSWORD=postgres123
REDIS_HOST=redis
SECRET_KEY=put_your_own_random_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Then:
```
docker compose up --build
```

That brings up the API, Postgres, and Redis together. Docs at `http://localhost:8000/docs`.

**Frontend:**

```
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, make an account, start shortening links.

## How the deployment pipeline works

Every push to main triggers a GitHub Actions workflow that SSHs into the AWS server using credentials stored as GitHub Secrets (`EC2_HOST`, `EC2_USER`, `EC2_KEY`), runs `git pull`, tears down the old containers, and rebuilds fresh. The live version updates itself on every push.

Since the EC2 instance gets stopped between sessions, the IP changes on restart, so the `EC2_HOST` secret needs updating whenever that happens. The real fix is an AWS Elastic IP, which keeps the address fixed for free as long as it's attached to a running instance.

## Setting up your own EC2 instance

1. Launch an EC2 instance (Ubuntu, t3.micro for free tier), download the key pair for SSH
2. In the security group, open port 22 for SSH and port 8000 for the API. Redis doesn't need a public port — it only talks to the API inside Docker's internal network
3. SSH in: `ssh -i "your-key.pem" ubuntu@YOUR_EC2_IP`
4. Install Docker:
   ```
   sudo apt update
   sudo apt install docker.io docker-compose-v2 -y
   sudo usermod -aG docker ubuntu
   ```
5. Clone the repo and make the same `.env` file as above, on the server
6. `docker compose up -d --build`
7. For auto-deploy, add your own `EC2_HOST`, `EC2_USER`, and `EC2_KEY` as GitHub Secrets in your fork — pushes to main deploy automatically from there
