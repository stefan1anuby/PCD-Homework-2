#!/bin/bash
sudo apt update -y
sudo apt install -y docker.io

gcloud auth configure-docker

sudo docker pull gcr.io/pcd-homework-2-455019/chat-app

sudo docker run -d -p 5000:5000 gcr.io/pcd-homework-2-455019/chat-app
