#!/bin/bash
####################################################################################################
#
# Prepares an Amazon Linux 2 instance for running the x-remove-server web server
#
# Usage: ./setup.sh

# Install docker on Amazon Linux 2
sudo yum install -y docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Create the /mnt/data dir for writing logs
sudo mkdir /mnt/data
sudo chown ec2-user:ec2-user /mnt/data
mkdir /mnt/data/logs
mkdir /mnt/data/api

# Format the /dev/xvdb disk
sudo mkfs -t ext4 /dev/xvdb
sudo mount /dev/xvdb /mnt/data

# Get the UUID of the /dev/xvdb disk
UUID=$(sudo blkid -s UUID -o value /dev/xvdb)

# Add the /dev/xvdb disk to /etc/fstab so it mounts on boot
echo "UUID=$UUID /dev/xvdb /mnt/data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
