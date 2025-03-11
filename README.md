### Background
Myko operates in a very similar way to HubSpace - this HACS integration is HubSpace-Homeassistant dressed up to look like Myko. Any issues with this integration should be directed here, and not at the HubSpace-Homeassistant developers.

Myko is reliant on a cloud connection which means this integration could break at any point. Not all
devices may be supported with and developer time will be required to add new devices. Supported
device types:

 * fan
   * On/Off
   * Speed
   * Preset mode
 * device-lock
   * Lock / Unlock
 * light
   * On/Off
   * Color Temperature
   * Color Sequences
   * Dimming
   * RGB
   * Not working
     * HS (missing data dump for this device)
     * RGBW (missing data dump for this device)
     * RGBWW (missing data dump for this device)
     * WHITE (missing data dump for this device)
     * XY (missing data dump for this device)
 * power-outlet
   * On/Off
 * switch
   * On/Off
 * landscape-transformer (missing data dump for this device)
   * On/Off
 * water-valve
   * Open / Close

### Config

Configuration is done through the `Add Integrations` rather than configuration.yaml.

### Information :
This integration talks to the Myko API to set and retrieve states for all
of your registered devices. Once  the devices are discovered, it will determine
device capability and show correctly within Home Assistant.

### Installation


#### UI (Preferred)
Add this repo as a custom repository in [HACS](https://hacs.xyz/). Add the Myko integration.

### Troubleshooting

 * I have a device in HubSpace that is not added to Home Assistant
   * Check the logs for any warning / errors around hubspace and report the issue.
   * If no warning / error messages exist around HubSpace, the device type is likely
     not supported. Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that did not discover
 * I have a device and its missing functionality
   * Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that is not working
     along with the broken functionality
 * I have a device and its functionality is not working
   * Refer to the troubleshooting section to grab anonymized logs and
     open a new issue with the logs and state the device that is not working
     along with the broken functionality
   * If the developers are unable to solve the problem with the anonymized data,
     the raw data may need to be provided

### Support for a new model
To support a new model, the states and metadata will need to be gathered. To accomplish
this, you will need to gather the data. There are two ways to grab this information:

 * Through a shell (target a specific device)
 * Through the UI

#### Shell
Gathering this information through the shell is preferred as you
can target the device you want. You must have a python
interpreter installed for this to work. After it is installed,
the following setup steps must be run:

 * (Optional) Use a virtualenv
   * Unix
     * ```bash
       python -m pip install virtualenv
       python -m virtualenv ~/.virtualenv/myko
       source ~/.virtualenv/hubspace/bin/activate
       ```
   * Windows
     * ```bat
       python -m pip install virtualenv
       python -m virtualenv "%userprofile%\.virtualenv\hubspace"
       %userprofile%\.virtualenv\hubspace\Scripts\activate.bat
       ```
 * Download requirements
   * ```sh
     python -m pip install requests "myko_async>=0.0.5" click
     ```
 * Goto your home directory
   * Unix
     * ```bash
       cd ~
       ```
   * Windows
     * ```bat
       cd  %userprofile%
       ```
 * Download the anonymizer code
   * ```bash
     python -c "import requests; data=requests.get('https://raw.githubusercontent.com/dvd604/Myko-Homeassistant/main/custom_components/myko/anonomyize_data.py').text; fh=open('anonomyize_data.py', 'w'); fh.write(data); fh.close();"
     ```
 * Run the anonymizer code (but fill in username and password)
   * Determine the device (gets child_id and friendly names)
     * Get all devices
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" get-devs
         ```
   * Gather data based on friendlyName or childID. This will create a .json file with the friendlyname in the current directory
     * Get devices based on a friendlyName
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" friendly-name --fn "<friendly name>"
         ```
     * Get devices based on a childId
       * ```python
         python anonomyize_data.py --username "<username>" --password "<password>" child-id --child_id "<child_id>"
         ```

#### Through the UI
Gathering data through the UI provides a less targeted approach to gathering data
as it will pull all devices. This may be required if a device cannot be fixed with
a normal data dump, or you are not comfortable running python on your system. It requires
the add-on `File Editor` or a similar add-on /  integration that enables you to download
files from Home Assistant. After  the file downloader has been installed onto Home
Assistant, the following steps are required to gather the data:

 * Enable Debug
   * Settings -> Devices & services -> Integrations -> hubspace -> Enable debug logging
 * Wait 30s - 60s for the files to generate
 * Open File Editor
 * Click the folder icon on the top left
 * Navigate to custom_components -> hubspace
 * Download the required files:
   * `_dump_hs_devices.json`: Anonymized device dumps consumed by the HubSpace integration
   * `_dump_hs_raw.json`: Raw data from the connector. This data is not anonymized
 * Disable debug
   * Settings -> Devices & services -> Integrations -> hubspace -> Disable debug logging

