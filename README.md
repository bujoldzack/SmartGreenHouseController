# SmartGreenHouseController

## Team: Zacharie & Murtaza

## Introduction
The **Smart Greenhouse Controller** project aims to develop an automated and remotely manageable system using a Raspberry Pi as the core component. This system will monitor and control key environmental conditions inside a greenhouse, such as temperature, soil moisture, and light intensity. The goal is to optimize plant growth and ensure that conditions remain within optimal thresholds.

## Solution Overview
The solution will be designed to read data from sensors, control actuators based on predefined thresholds, and allow for remote monitoring and control through a web-based dashboard. The data will be managed through AWS IoT Core and stored in DynamoDB, while the dashboard will be built using ThingsBoard to provide an intuitive interface for real-time observation and manual actuator control.

### Key Features:
- **Real-time Monitoring**: Track temperature, soil moisture, and light levels inside the greenhouse.
- **Automated Control**: Automatically activate actuators such as the fan, water pump, and grow lights based on sensor readings.
- **Remote Dashboard Access**: Monitor data and manually control actuators via a ThingsBoard dashboard.
- **Historical Data Storage**: Maintain records of environmental data in AWS DynamoDB.
- **Alerts and Notifications**: Send email alerts when sensor data exceeds defined thresholds.

## Deliverables Timetable
- **Wednesday, November 13**: Initial project setup and planning.
- **Wednesday, November 20**: Hardware integration, Python scripts for sensor data collection, and basic actuator control.
- **Wednesday, November 27**: Integration with AWS IoT Core, historical data tracking, and ThingsBoard dashboard development.
- **Wednesday, December 4**: Final dashboard implementation, documentation, and project demonstration.

## List of Components
- **Raspberry Pi**
- **Temperature Sensor** (DS18B20)
- **Soil Moisture Sensor**
- **Light Sensor** (Photoresistor)
- **LED** for simulating the water pump
- **Fan** for HVAC system simulation
- **2 LEDs** for grow lights
- **Additional items**: Jumper wires, breadboard, GPIO Extension Board

# AWS IoT Configuration
This section outlines the necessary configuration settings for connecting to AWS IoT. Below is a table with the required parameters and their values:

| Parameter            | Description                                                                 | Example/Value                             |
|----------------------|-----------------------------------------------------------------------------|-------------------------------------------|
| **AWS_HOST**         | The endpoint for AWS IoT. You can find this on the Settings page in the AWS IoT menu, under the "Device data endpoint" section. | `your-endpoint.iot.region.amazonaws.com`  |
| **AWS_ROOT_CA**      | Path to the AWS IoT root certificate. This file is usually downloaded from the AWS IoT console. | `/home/pi/certs/aws_root.pem`             |
| **AWS_CLIENT_CERT**  | Path to the AWS IoT client certificate. This file is usually downloaded from the AWS IoT console. | `/home/pi/certs/aws_client.crt`           |
| **AWS_PRIVATE_KEY**  | Path to the AWS IoT private key. This file is usually downloaded from the AWS IoT console. | `/home/pi/certs/aws_private.key`          |
| **CLIENT_ID**        | A unique identifier for the client connecting to the IoT service. In simple implementations, this can be any value. | `fromPi`                                  |
| **TOPIC**            | The topic to which data is published. Choose a meaningful name for your project. | `champlain/device/+/data`        |



# Initial Dashboard Setup
![image](https://github.com/user-attachments/assets/4aa10efc-ea4d-44bd-89ad-278861decc4e)
