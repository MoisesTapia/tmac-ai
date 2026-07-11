# =====================================================================
# Cómputo — Launch Template + Auto Scaling Group + Elastic Beanstalk
# =====================================================================

resource "aws_launch_template" "app" {
  name_prefix   = "${var.project}-lt-"
  image_id      = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    arn = aws_iam_instance_profile.app.arn
  }

  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size = 30
      encrypted   = true
      kms_key_id  = aws_kms_key.main.arn
    }
  }
}

resource "aws_autoscaling_group" "app" {
  name                = "${var.project}-asg"
  min_size            = 2
  max_size            = 6
  desired_capacity    = 2
  vpc_zone_identifier = [aws_subnet.private_app_a.id, aws_subnet.private_app_b.id]
  target_group_arns   = [aws_lb_target_group.app.arn]

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }
}

# Elastic Beanstalk — despliega la imagen de contenedor desde ECR
resource "aws_elastic_beanstalk_application" "main" {
  name        = "${var.project}-eb"
  description = "Aplicación principal desplegada vía Elastic Beanstalk"
}

resource "aws_elastic_beanstalk_environment" "main" {
  name                = "${var.project}-eb-env"
  application         = aws_elastic_beanstalk_application.main.name
  solution_stack_name = "64bit Amazon Linux 2 v3.7.1 running Docker"

  setting {
    namespace = "aws:ec2:vpc"
    name      = "VPCId"
    value     = aws_vpc.main.id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = aws_subnet.private_app_a.id
  }
}
