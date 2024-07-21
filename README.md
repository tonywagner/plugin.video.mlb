[![GitHub release](https://img.shields.io/github/release/tonywagner/plugin.video.mlb.svg)](https://github.com/tonywagner/plugin.video.mlb/releases)
![License](https://img.shields.io/badge/license-GPL%20(%3E%3D%202)-orange)
[![Contributors](https://img.shields.io/github/contributors/tonywagner/plugin.video.mlb.svg)](https://github.com/tonywagner/plugin.video.mlb/graphs/contributors)

# Features

* Watch in Kodi and/or a web browser
* Watch recaps and highlights
* Watch free games with an account
* Watch all non-blackout games with a valid subscription

# Disclaimer

Blackout restrictions apply.

# Installation

Choose any one of these three methods to install and run:

1. Kodi version 21 (Omega) or newer  
   * [Download and install Kodi](https://kodi.tv/download/) (see this [guide](https://troypoint.com/how-to-install-kodi-on-fire-tv/) for installing on a Fire Stick)  
   * Download the [latest release ZIP file](https://github.com/tonywagner/plugin.video.mlb/releases/latest/download/plugin.video.mlb.zip) and copy to your Kodi device (or just use code 278937 in the Downloader app on your Fire Stick)  
   * Launch Kodi and install the ZIP in the Addons section (Kodi will prompt you to allow installing addons from unknown sources)  
   * __**Note:** Windows users must also install the [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#latest-microsoft-visual-c-redistributable-version) version 14.40.33810.0 or later__  

2. Python (3.11 or newer) with the "requests" module installed  
   * [Download and install Python 3](https://www.python.org/downloads/) if you don't have it already  
   * Install the Python "requests" module like `pip install requests` or `pip3 install requests`
   * [Download and unzip the [latest release ZIP file](https://github.com/tonywagner/plugin.video.mlb/releases/latest/download/plugin.video.mlb.zip)  
   * Run the service script like `python plugin.video.mlb/service.py` or `python3 plugin.video.mlb/service.py`

3. [Docker](https://hub.docker.com/r/tonywagner/plugin.video.mlb)
   * Download the [docker-compose.yml](https://raw.githubusercontent.com/tonywagner/plugin.video.mlb/master/docker-compose.yml) file, update the time zone in the file to your own, and create and start the container like '''docker compose up --detach'''  
   * Alternately, you can run the command '''docker run -d --name plugin.video.mlb --env TZ="America/New_York" -p 5714:5714 --volume /absolute/path/to/your/data:/plugin.video.mlb/data tonywagner/plugin.video.mlb''' (substituting your own time zone, of course)  

# Usage

Once installed, open any web browser on your network and navigate to http://IP-ADDRESS:5714 (using the IP address of the device running Kodi or the Python script).

If you installed within Kodi, you can access it within the Addons section of Kodi too.

# Notes

Intended as a replacement for both [plugin.video.mlbtv](https://github.com/eracknaphobia/plugin.video.mlbtv) and [mlbserver](https://github.com/tonywagner/mlbserver)

