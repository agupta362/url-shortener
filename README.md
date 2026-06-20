# URL Shortener API

A full-stack URL shortener with JWT authentication, click analytics, and a React frontend. Backend built with Python FastAPI and PostgreSQL, containerized with Docker, deployed on AWS EC2 with automated CI/CD via GitHub Actions.

 The AWS EC2 instance for this project is not kept running continuously to stay within free tier limits. The IP address changes each time the instance is stopped and restarted. Follow the "Run Locally" section below to test the full application, or see "Deploy Your Own EC2 Instance" to host it yourself.

## Features

- User registration and login with JWT authentication (access + refresh tokens)
- Passwords hashed with bcrypt, never stored in plain text
- Create short URLs with optional custom codes
- Click tracking with timestamps for analytics
- Each user can only see and manage their own URLs
- React frontend for registering, logging in, and managing links
- Dockerized with Docker Compose
- Automated deployment via GitHub Actions CI/CD

## Tech Stack

Backend: Python, FastAPI, PostgreSQL, psycopg2, Passlib (bcrypt), python-jose (JWT)
**Frontend:** React, Vite
**Infrastructure:** Docker, Docker Compose, AWS EC2, GitHub Actions

## API Routes

| Method | Route | Auth Required | Description |

| POST | /register | No | Create a new account |
| POST | /login | No | Log in, returns access + refresh tokens |
| POST | /refresh | No | Get a new access token using refresh token |
| POST | /urls | Yes | Create a new short URL |
| GET | /urls | Yes | Get all URLs for the logged-in user |
| GET | /{short_code} | No | Redirects to the original URL and logs the click |

## How Authentication Works

1. User registers — password is hashed with bcrypt before being stored
2. User logs in — server verifies the password hash and issues an access token (30 min) and a refresh token (7 days)
3. Access token is sent in the `Authorization: Bearer <token>` header on every protected request
4. When the access token expires, the refresh token is used to get a new one without logging in again

## Run Locally

**Backend:**

1. Clone the repo:
   ```
   git clone https://github.com/agupta362/url-shortener.git
   cd url-shortener
   ```

2. Create a `.env` file in the root with:
   ```
   DB_HOST=db
   DB_NAME=urlshortener
   DB_USER=postgres
   DB_PASSWORD=postgres123
   SECRET_KEY=your_own_random_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ```

3. Start the backend:
   ```
   docker compose up --build
   ```

4. API docs available at: `http://localhost:8000/docs`

**Frontend:**

1. In a separate terminal:
   ```
   cd frontend
   npm install
   npm run dev
   ```

2. Open `http://localhost:5173`

3. Register an account, log in, and start creating short links

## How GitHub Actions CI/CD Is Set Up

Every push to the `main` branch automatically deploys to AWS through `.github/workflows/deploy.yml`:

1. GitHub spins up a temporary runner
2. It SSHs into the AWS EC2 server using credentials stored in GitHub Secrets (`EC2_HOST`, `EC2_USER`, `EC2_KEY`)
3. On the server it runs:
   ```
   git pull
   docker compose down
   docker compose up -d --build
   ```
4. The live API is updated automatically with zero manual steps

**Important:** GitHub Secrets store the EC2 IP and SSH key. Since the EC2 instance is stopped between sessions to conserve free tier hours, the IP address changes on restart, and the `EC2_HOST` secret must be updated to the new IP for the pipeline to keep working. A permanent fix is attaching an AWS Elastic IP (free as long as it's associated with a running instance) so the address never changes.

## Deploy Your Own EC2 Instance

To host this yourself on AWS:

1. Launch an EC2 instance (Ubuntu, t3.micro for free tier) with a key pair for SSH access
2. In the instance's security group, add inbound rules allowing traffic on port 22 (SSH), 8000 (API)
3. SSH into the instance:
   ```
   ssh -i "your-key.pem" ubuntu@YOUR_EC2_IP
   ```
4. Install Docker:
   ```
   sudo apt update
   sudo apt install docker.io docker-compose-v2 -y
   sudo usermod -aG docker ubuntu
   ```
5. Clone this repo and create the `.env` file on the server (same contents as the local setup above):
   ```
   git clone https://github.com/agupta362/url-shortener.git
   cd url-shortener
   nano .env
   ```
6. Run it:
   ```
   docker compose up -d --build
   ```
7. To enable auto-deployment, add your EC2 IP, SSH username, and private key as GitHub Secrets (`EC2_HOST`, `EC2_USER`, `EC2_KEY`) in your forked repo's settings — every push to main will then deploy automatically.

## What I Learned Building This

- Designing and implementing JWT-based authentication from scratch, including access/refresh token rotation
- Password security with bcrypt hashing
- Building a normalized PostgreSQL schema with foreign key relationships across users, URLs, and click events
- Containerizing a multi-service application with Docker Compose
- Setting up a full CI/CD pipeline with GitHub Actions for automated deployment
- Connecting a React frontend to a custom-built REST API
