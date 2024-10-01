# EC2 Instance Setup Guide

This guide provides steps to set up and interact with the Amazon EC2 instance for the Solar Tracker project. The IP address for the instance is http://18.191.208.137

## Prerequisites

1. Ensure you have the private key `solarkey.pem` file, which is required to connect to the EC2 instance. Move this file to your desktop for easy access.

## Connecting to the EC2 Instance

1. **Open a terminal** and navigate to your desktop directory:
   ```bash
   cd ~/Desktop
   ```

2. **Modify the permissions** of the private key file to be more secure:
   ```bash
   chmod 400 solarkey.pem
   ```

3. **SSH into the EC2 instance** using the following command:
   ```bash
   ssh -i "solarkey.pem" ec2-user@18.191.208.137
   ```

   This will log you into the EC2 instance.

## Running the Solar Tracker Backend

1. **Navigate to the Solar Tracker directory**:
   ```bash
   ls
   cd solar-tracker
   ```

2. **Start the backend server**:
   ```bash
   sudo python3 app.py
   ```

## Sending Data to the Server

Once the backend server is running, you can use the following `curl` commands to send data:

1. **Open a new terminal** and run the following `curl` command to send sensor data (for example, humidity):
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"sensor": "humidity", "value": 55.3}' http://18.191.208.137/data
   ```

## Viewing Received Data

1. After sending data, you can view it by running the following command in the EC2 instance terminal:
   ```bash
   cat received_data.json
   ```
