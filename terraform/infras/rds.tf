# ============================================================
# AWS RDS (managed PostgreSQL) — replaces the self-hosted
# Postgres container for the AWS/production path.
# ============================================================

# --- Default VPC + its subnets (no extra cost) --------------
# RDS needs to know which network it lives in. We reuse the
# account's default VPC and its subnets.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# --- Security group for the database ------------------------
# Firewall rule: allow Postgres (5432) ONLY from the EC2's
# security group — never from the public internet.
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow Postgres only from the API EC2 security group"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api_sg.id] # source = EC2 SG, not an IP
    description     = "Postgres from API server only"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-rds-sg"
    Project = var.project_name
  }
}

# --- Subnet group ------------------------------------------
# RDS places the DB in these subnets.
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Name    = "${var.project_name}-db-subnet-group"
    Project = var.project_name
  }
}

# --- The managed PostgreSQL instance -----------------------
resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"

  instance_class    = "db.t3.micro" # free-tier friendly
  allocated_storage = 20            # GB, free-tier level
  storage_type      = "gp2"

  db_name  = "urlshortener"
  username = "postgres"
  password = var.db_password # reuse existing variable

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  publicly_accessible = false # private: only reachable inside the VPC
  skip_final_snapshot = true  # clean teardown for a lab
  deletion_protection = false

  tags = {
    Name    = "${var.project_name}-db"
    Project = var.project_name
  }
}
