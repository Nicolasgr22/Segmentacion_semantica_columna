terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }

  # PASO 2: Descomentar después del primer apply (que crea el bucket de estado).
  # Luego ejecutar: terraform init -migrate-state
  #
  # backend "s3" {
  #   bucket  = "anferiro-maia-proyecto-final-state"
  #   key     = "columna/terraform.tfstate"
  #   region  = "us-east-1"
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.aws_region
}
