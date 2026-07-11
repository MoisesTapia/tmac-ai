# =====================================================================
# Providers — Región A (primaria) y Región B (warm standby)
# =====================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "aws" {
  alias  = "standby"
  region = "us-west-2"
}

variable "project" {
  type    = string
  default = "enterprise-app"
}

variable "domain_name" {
  type    = string
  default = "app.example.com"
}
