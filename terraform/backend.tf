terraform {
  backend "s3" {
    bucket         = "terraform-state-url-shortener-797240615047"
    key            = "url-shortener/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "terraform-state-locks"
    use_lockfile   = true
    encrypt        = true
  }
}