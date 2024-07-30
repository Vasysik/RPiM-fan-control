# RPiM-fan-control Module for RPiModules

## Description

RPiM-fan-control is a module for [RPiModules](https://github.com/Vasysik/RPiModules) that allows you to control the fan speed on your Raspberry Pi (RPi) based on the temperature. This module is designed to enhance the cooling performance of your RPi and prevent overheating.

## Installation

1. Clone the RPiM-fan-control module from the GitHub repository to the 'modules' directory within your [RPiModules](https://github.com/Vasysik/RPiModules).

   ```
   git clone https://github.com/Vasysik/RPiM-fan-control.git /path/to/RPiModules/modules/fan_control
   ```

2. Open the `modules.json` file located in your RPiModules directory and add the following configuration for the fan_control module:

   ```json
   "fan_control": {
       "route": "fan_control",
       "icon": "fan_control/static/fan_control_icon.png",
       "name": "Fan Control",
       "enable": true
   }
   ```

3. Configure the `config.json` file within the fan_control module according to your requirements. You can set the temperature thresholds for turning the fan on and off, as well as configure the InfluxDB settings for data logging.

4. Install the `fan_control.service` service for your RPiModules installation.

   ```
   sudo cp /path/to/RPiModules/modules/fan_control/fan_control.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable fan_control.service
   sudo systemctl start fan_control.service
   ```

## Usage

Once the installation and configuration are complete, you can access the fan_control module through your [RPiModules](https://github.com/Vasysik/RPiModules) web interface. You can set the temperature thresholds for turning the fan on and off in the web interface.

## Contributing

Contributions to the RPiM-fan-control module are welcome! If you have any suggestions, bug reports, or feature requests, please open an issue on the GitHub repository. Pull requests are also encouraged.
