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
from tzlocal import get_localzone
from xml.sax.saxutils import XMLGenerator
import collections
import hashlib
import re
import operator
import os
import sys
import xml.etree.ElementTree as ET
import yaml

fname_re = re.compile("^tv-([0-9]{8})\\.xmltv$")
ts_fmt = "%Y%m%d%H%M%S"
tz = get_localzone()
tag = "tag:xmltv-new.uuid.uk,2014-07-04:"

now = tz.localize(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None))

def process(channels, file):
		tree = ET.parse(file)
		root = tree.getroot()
		programmes = []

		for channel in root.findall("./channel"):
			id = channel.get("id")
			if id in channels:
				channels[id] = channel.findtext("display-name", default="")

		for programme in root.findall("./programme/new/.."):
			channel = programme.get("channel")
			if channel in channels:
				data = {}
				data["channel"] = channel
				data["start"] = tz.localize(datetime.strptime(programme.get("start"), ts_fmt))
				data["stop"] = tz.localize(datetime.strptime(programme.get("stop"), ts_fmt))
				data["title"] = programme.findtext("title", default="")
				data["subtitle"] = programme.findtext("sub-title", default="")
				data["desc"] = programme.findtext("desc", default="")
				data["categories"] = [x.text for x in programme.findall("category")]
				data["directors"] = [x.text for x in programme.findall("credits/director")]
				data["actors"] = [x.text for x in programme.findall("credits/actor")]

				programmes.append(data)

		return programmes

def output(channels, data):
	g = XMLGenerator(sys.stdout, "UTF-8")
	g.startDocument()
	print()

	g.startElement("feed", {"xmlns": "http://www.w3.org/2005/Atom"})

	g.startElement("title", {})
	g.characters("XMLTV new series")
	g.endElement("title")

	g.startElement("id", {})
	g.characters(tag + "0")
	g.endElement("id")

	g.startElement("updated", {})
	g.characters(now.isoformat())
	g.endElement("updated")
	print()

	for programme in data:
		g.startElement("entry", {})

		g.startElement("title", {})
		title = "[" + channels[programme["channel"]] + "] " + programme["title"]
		if programme["subtitle"]:
			title += " (" + programme["subtitle"] + ")"
		g.characters(title)
		g.endElement("title")

		g.startElement("id", {})
		g.characters(tag + programme["channel"]
			+ ":" + programme["start"].strftime(ts_fmt)
			+ ":" + programme["stop"].strftime(ts_fmt)
			+ ":" + hashlib.sha256(programme["title"].encode("UTF-8")).hexdigest())
		g.endElement("id")

		g.startElement("published", {})
		g.characters(programme["start"].isoformat())
		g.endElement("published")

		for category in programme["categories"]:
			g.startElement("category", {"term": category})
			g.endElement("category")

		g.startElement("content", {"type": "xhtml"})
		g.startElement("div", {"xmlns": "http://www.w3.org/1999/xhtml"})
		g.startElement("p", {})
		g.characters(programme["desc"])
		g.endElement("p")

		if programme["directors"]:
			g.characters("Directors:")
			g.startElement("ul", {})
			for director in programme["directors"]:
				g.startElement("li", {})
				g.characters(director)
				g.endElement("li")
			g.endElement("ul")

		if programme["actors"]:
			g.characters("Cast:")
			g.startElement("ul", {})
			for actor in programme["actors"]:
				g.startElement("li", {})
				g.characters(actor)
				g.endElement("li")
			g.endElement("ul")
		g.endElement("div")
		g.endElement("content")

		g.endElement("entry")
		print()

	g.endElement("feed")
	g.endDocument()
	print()

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
			if tz.localize(datetime.strptime(fname_re.match(file).group(1), "%Y%m%d")) >= now:
				programmes += process(channels, os.path.join(config["data_dir"], file))

	programmes = sorted(programmes, key=operator.itemgetter("start", "stop", "channel", "title", "subtitle"), reverse=True)
	output(channels, programmes)

if __name__ == "__main__":
	main()
