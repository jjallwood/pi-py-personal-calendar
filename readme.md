# Using PYCHARM remote develop the code onto a PI

This was difficult to setup for remote Raspberry PI dev.
The general instructions for remote Python development using Pycharm, a Raspberry PI and SSH are [here](https://www.hackster.io/Jolley71717/connect-jetbrains-pycharm-to-raspberry-pi-72be15).

After securing an SSH connection, we then used the pycharm interpreter virtual env to manage the packages the project needed to run.
This involved installing the following dependencies.
I assume this is because the virtual environment isolates it's dependencies from the system dependencies to avoid collisions. 

```json
{
  "Pillow": "9.5.0",
  "RPI.GPIO": "0.7.1",
  "numpy": "1.25.2",
  "inky": "1.5.0"
}
```

To get numpy to work we had to manually install the following dependency onto the pi `sudo apt-get install libatlas-base-dev`.

To get PIL to work you need to install Pillow as a python package dependeny.
Pillow did not work until we ran the `sudo apt install libjpeg-dev zlib1g-dev` on the pi.

To get the pin connections to work from python we needed to install the `RPi.GPIO` package with pip.

# Microsoft Graph Connect

App registration was done via the azure [portal](https://portal.azure.com/).
To be able to read calendar info you need to assign the `Microsoft Graph - Calendars.Read` API permissions to your app.
You then need to set your azure application ID to the `APP_ID` python environment variable.

# Running Python script on a schedule on Pi

To set the job to run on a regular cadence we set up the following cron script on the PI unix OS.
As this script uses some setup from env variables etc, we setup a `.sh` script on the server to run through those pre-requisites. 

Below are the steps to run the script every 20 mins. 

```
// crontab -e
*/20 * * * * [path-to-sh] 1>/dev/null 2>[path-for-cron-err-log]
```

To enable cron debug logging we had to comment out the cron line in the rsyslog.conf file.

```
open /etc/rsyslog.conf
service rsyslog restart
service cron restart
```

We also had to ensure our `.sh` script had no access permissions.

```
chmod +x [path-to-sh]
```