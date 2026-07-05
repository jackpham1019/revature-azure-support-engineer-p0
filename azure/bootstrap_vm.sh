#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io docker-compose-v2 docker-buildx git
systemctl enable --now docker

rm -rf /home/azureuser/2406_azure_support_engineer
git clone https://github.com/jackpham1019/revature-azure-support-engineer-p0.git /home/azureuser/revature-azure-support-engineer-p0

cd /home/azureuser/revature-azure-support-engineer-p0/api_demo

docker compose up -d --build

docker compose ps
sleep 5
curl -I http://localhost:8081/health || curl -I http://localhost:8081/

#Fix folder permissions
chown -R azureuser:azureuser /home/azureuser/revature-azure-support-engineer-p0