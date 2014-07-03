#!/usr/bin/env python3

#  xmltv-new - XMLTV new series notifier
#
#  Copyright ©2014 Simon Arlott
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from tabulate import tabulate
import collections
import re
import operator
import os
import xml.etree.ElementTree as ET
import yaml

fname_re = re.compile("^tv-([0-9]{8})\\.xmltv$")
ts_fmt = "%Y%m%d%H%M%S"

now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

def process(channels, file):
		tree = ET.parse(file)
		root = tree.getroot()
		programmes = []

		for channel in root.findall("./channel"):
			id = channel.get("id")
			if id in channels:
				channels[id] = channel.findtext("display-name", default="")

		for programme in root.findall("./programme/new/.."):
			start = str(datetime.strptime(programme.get("start"), ts_fmt))
			stop = str(datetime.strptime(programme.get("stop"), ts_fmt))
			channel = programme.get("channel")
			title = programme.findtext("title", default="")
			subtitle = programme.findtext("sub-title", default="")

			if channel in channels:
				channel = channels[channel]
				programmes.append([channel, title, subtitle, start, stop])

		return programmes

def main(config="config", base=os.getcwd()):
	config = yaml.safe_load(open(os.path.join(base, config), "rt", encoding="UTF-8"))
	config.setdefault("data_dir", os.getcwd())
	config.setdefault("channels", [])

	channels = dict.fromkeys([channel["id"] for channel in config["channels"]], "")
	programmes = []

	for root, dirs, files in os.walk(config["data_dir"]):
		del dirs[:]
		files = sorted(list(filter(fname_re.search, files)))

		for file in files:
			if datetime.strptime(fname_re.match(file).group(1), "%Y%m%d") >= now:
				programmes += process(channels, os.path.join(config["data_dir"], file))

	programmes = sorted(programmes, key=operator.itemgetter(3, 4, 0, 1, 2))
	print(tabulate(programmes, headers=["Channel", "Title", "Subtitle", "Start", "Stop"], tablefmt="grid"))

if __name__ == "__main__":
	main()
