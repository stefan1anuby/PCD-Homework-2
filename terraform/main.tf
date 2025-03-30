provider "google" {
  project = "pcd-homework-2-455019"
  region  = "europe-west1"
  zone    = "europe-west1-b"
}

resource "google_compute_network" "chatapp_vpc" {
  name                    = "chatapp-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_router" "chatapp_router" {
  name    = "chatapp-router-new"
  network = google_compute_network.chatapp_vpc.id
  region  = "europe-west1"
}

resource "google_compute_router_nat" "chatapp_nat" {
  name                               = "chatapp-nat"
  router                             = google_compute_router.chatapp_router.name
  region                             = google_compute_router.chatapp_router.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

resource "google_compute_route" "default_nat_route" {
  name            = "default-nat-route"
  network         = google_compute_network.chatapp_vpc.id
  dest_range      = "0.0.0.0/0"
  next_hop_gateway = "default-internet-gateway"
}

resource "google_compute_firewall" "allow_egress" {
  name    = "allow-egress"
  network = google_compute_network.chatapp_vpc.id

  allow {
    protocol = "all"
  }

  direction          = "EGRESS"
  destination_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = google_compute_network.chatapp_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]
}

resource "google_compute_subnetwork" "chatapp_subnet" {
  name                     = "chatapp-subnet"
  region                   = "europe-west1"
  network                  = google_compute_network.chatapp_vpc.id
  ip_cidr_range            = "10.0.0.0/24"
  private_ip_google_access = true
}

resource "google_compute_global_address" "private_ip_alloc" {
  name          = "private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.chatapp_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.chatapp_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
}

resource "google_sql_database_instance" "db_instance" {
  name             = "chatapp-db-instance"
  region           = "europe-west1"
  database_version = "POSTGRES_13"

  settings {
    tier = "db-f1-micro"
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.chatapp_vpc.id
    }

    backup_configuration {
      enabled   = true
      start_time = "03:00"
    }
  }
}

resource "google_sql_database" "chatdb" {
  name     = "chatdb"
  instance = google_sql_database_instance.db_instance.name
}

resource "google_sql_user" "db_user" {
  name     = "postgres"
  instance = google_sql_database_instance.db_instance.name
  password = "postgres"
}

resource "google_compute_firewall" "allow_http" {
  name    = "allow-http"
  network = google_compute_network.chatapp_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "5000"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "allow-http-https"
  network = google_compute_network.chatapp_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
}

resource "google_compute_instance_template" "app_template" {
  name         = "chat-app-template"
  machine_type = "n1-standard-1"
  region       = "europe-west1"

  service_account {
    email  = "my-service-account@pcd-homework-2-455019.iam.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  disk {
    boot         = true
    auto_delete  = true
    source_image = "ubuntu-os-cloud/ubuntu-2004-focal-v20210129"
  }

  network_interface {
    network    = google_compute_network.chatapp_vpc.id
    subnetwork = google_compute_subnetwork.chatapp_subnet.id
  }

  metadata_startup_script = file("template.sh")
}

resource "google_compute_instance_template" "new_app_template" {
  name_prefix   = "chat-app-template-new-"
  machine_type  = "n1-standard-1"
  region        = "europe-west1"
  
  service_account {
    email  = "my-service-account@pcd-homework-2-455019.iam.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  disk {
    boot         = true
    auto_delete  = true
    source_image = "ubuntu-os-cloud/ubuntu-2004-focal-v20210129"
  }

  network_interface {
    network    = google_compute_network.chatapp_vpc.id
    subnetwork = google_compute_subnetwork.chatapp_subnet.id
  }

  metadata = {
    startup-script = file("template.sh")
  }
}

resource "google_compute_instance_group_manager" "app_group" {
  name               = "chat-app-group"
  base_instance_name = "chat-app"
  zone               = "europe-west1-b"
  target_size        = 2

  lifecycle {
    create_before_destroy = true
  }
  version {
    instance_template = google_compute_instance_template.new_app_template.id
  }

  named_port {
    name = "http"
    port = 5000
  }

  update_policy {
    type                    = "PROACTIVE"
    minimal_action          = "REPLACE"
    max_surge_fixed         = 1
    max_unavailable_fixed   = 1
    replacement_method      = "SUBSTITUTE"
  }

  depends_on = [google_compute_instance_template.new_app_template]
}

resource "google_compute_health_check" "app_health_check" {
  name = "app-health-check"

  http_health_check {
    port          = 5000
    request_path  = "/health"
  }
}

resource "google_compute_backend_service" "app_backend" {
  name          = "app-backend"
  health_checks = [google_compute_health_check.app_health_check.id]
  protocol      = "HTTP"

  backend {
    group = google_compute_instance_group_manager.app_group.instance_group
  }

  log_config {
    enable = true
    sample_rate = 1.0
  }
}

resource "google_compute_url_map" "app_url_map" {
  name = "app-url-map"

  default_service = google_compute_backend_service.app_backend.id
}

resource "google_compute_target_http_proxy" "app_http_proxy" {
  name    = "app-http-proxy"
  url_map = google_compute_url_map.app_url_map.id
}

resource "google_compute_global_forwarding_rule" "app_forwarding_rule" {
  name       = "app-forwarding-rule"
  target     = google_compute_target_http_proxy.app_http_proxy.id
  port_range = "5000"
}

output "load_balancer_ip" {
  value = google_compute_global_forwarding_rule.app_forwarding_rule.ip_address
}
