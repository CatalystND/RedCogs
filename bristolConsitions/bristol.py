#!/usr/bin/python3
import urllib.request, re
page = str(urllib.request.urlopen('https://www.bristolmountain.com/conditions/'))
# print(page.read())

cometRegex = re.compile("Comet Express Quad")
cometStatus = re.search("Comet Express Quad(.{20})", page)
print(cometStatus)
