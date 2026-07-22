terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_security_group" "api_sg" {
  name        = "${var.project_name}-sg"
  description = "Security group for ${var.project_name} API server"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "API"
  }

  ingress {
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Job Tracker API"
  }

  ingress {
    from_port   = 8002
    to_port     = 8002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "URL Shortener API"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "api_server" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  vpc_security_group_ids      = [aws_security_group.api_sg.id]
  key_name                    = var.key_name
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name
  user_data_replace_on_change = true

  user_data = <<-EOF
#!/bin/bash
set -eux
apt-get update -y
apt-get install -y docker.io git awscli curl
usermod -aG docker ubuntu
systemctl enable docker
systemctl start docker

# Installing Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

PROJECT="${var.project_name}"
REGION="${var.aws_region}"

# Waitting for IAM instance profile credentials before calling SSM.
until aws sts get-caller-identity --region "$REGION" &>/dev/null; do
  sleep 5
done

DB_PASSWORD=$(aws ssm get-parameter --name "/$PROJECT/DB_PASSWORD" --with-decryption --region $REGION --query Parameter.Value --output text)
SECRET_KEY=$(aws ssm get-parameter --name "/$PROJECT/SECRET_KEY" --with-decryption --region $REGION --query Parameter.Value --output text)
DB_NAME=$(aws ssm get-parameter --name "/$PROJECT/DB_NAME" --region $REGION --query Parameter.Value --output text)
DB_USER=$(aws ssm get-parameter --name "/$PROJECT/DB_USER" --region $REGION --query Parameter.Value --output text)
ALGORITHM=$(aws ssm get-parameter --name "/$PROJECT/ALGORITHM" --region $REGION --query Parameter.Value --output text)
ACCESS_TOKEN_EXPIRE_MINUTES=$(aws ssm get-parameter --name "/$PROJECT/ACCESS_TOKEN_EXPIRE_MINUTES" --region $REGION --query Parameter.Value --output text)
REFRESH_TOKEN_EXPIRE_DAYS=$(aws ssm get-parameter --name "/$PROJECT/REFRESH_TOKEN_EXPIRE_DAYS" --region $REGION --query Parameter.Value --output text)

cd /home/ubuntu
git clone https://github.com/agupta362/url-shortener.git
cd url-shortener

cat > .env << ENVEOF
DB_HOST=db
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
REDIS_HOST=redis
SECRET_KEY=$SECRET_KEY
ALGORITHM=$ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES=$ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS=$REFRESH_TOKEN_EXPIRE_DAYS
ENVEOF

chown ubuntu:ubuntu .env
docker compose up -d --build
  EOF

  tags = {
    Name    = "${var.project_name}-server"
    Project = var.project_name
  }
}