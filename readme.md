# Using PYCHARM remote develop the code onto a PI

This was difficult to setup for remove dev.
The general instructions for SSH connection are [here](https://www.hackster.io/Jolley71717/connect-jetbrains-pycharm-to-raspberry-pi-72be15).

After securing an SSH connection, we then used the pycharm interpreter virtual env to manage the packages the project needed to run.
This involved installing the following dependencies.
I assume so the virtual environment isolates it's dependencies from the system dependencies to avoid collisions. 

```json
{
  "Pillow": "9.5.0",
  "RPI.GPIO": "0.7.1",
  "numpy": "1.25.2",
  "inky": "1.5.0"
}
```

To get numpy to work we had to manually install the following package onto the pi `sudo apt-get install libatlas-base-dev`.

To get PIL to work you need to install Pillow as a python package dependeny.
Pillow did not work until we ran the `sudo apt install libjpeg-dev zlib1g-dev`.

To get the pin connections to work from python we needed to install the `RPi.GPIO` package.