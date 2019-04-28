#!/usr/bin/env python
""" Python script to generate a stub README.md files from a plugin.json file """
import json
import argparse
import os
import sys
import io
import datetime
import pprint
import tempfile

currentpluginmetadataversion = 2

validPluginTypes = ["core", "ui", "binaryview", "architecture", "helper"]
validApis = ["python2", "python3"]
validPlatforms = ["Darwin", "Windows", "Linux"]
requiredLicenseKeys = ["name", "text"]

def validateList(data, name, validList):
	if name not in data:
		print("Warning: '{}' filed doesn't exist".format(name))
		return False
	elif not isinstance(data[name], list):
		print("Error: '{}' field isn't a list".format(name))
		return False

	success = True
	for item in data[name]:
		if item not in validList:
			print("Error: plugin {}: {} not one of {}".format(name, item, validList))
			success = False
	return success

def validateString(data, name):
	if name not in data:
		print("Error: '{}' field doesn't exist".format(name))
		return False
	elif not isinstance(data[name], unicode) and not isinstance(data[name], str):
		print("Error: '{}' field is {} not a string".format(name, type(data[name])))
		return False
	return True

def validateInteger(data, name):
	if name not in data:
		print("Error: '{}' field doesn't exist.".format(name))
		return False
	elif not isinstance(data[name], int):
		print("Error: '{}' is {} not an integer value".format(name, type(data[name])))
		return False
	return True

def validateStringMap(data, name, validKeys, requiredKeys=None):
	if name not in data:
		print("Error: '{}' field doesn't exist.".format(name))
		return False
	elif not isinstance(data[name], dict):
		print("Error: '{}' is {} not a dict type".format(name, type(data[name])))
		return False

	success = True
	if requiredKeys is not None:
		for key in requiredKeys:
			if key not in data[name]:
				print("Error: required subkey '{}' not in {}".format(key, name))
				success = False

	for key, value in data[name].items():
		if key not in validKeys:
			print("Error: key '{}' not is not in the set of valid keys {}".format(key, validKeys))
			success = False

	return success

def validateRequiredFields(data):
	success = validateInteger(data, "pluginmetadataversion")
	if success:
		if data["pluginmetadataversion"] != currentpluginmetadataversion:
			print("Error: 'pluginmetadataversion' is not the correct version")
			success = False
	else:
		print("Current version is {}".format(currentpluginmetadataversion))

	success &= validateString(data, "name")
	success &= validateList(data, "type", validPluginTypes)
	success &= validateList(data, "api", validApis)
	success &= validateString(data, "description")
	success &= validateString(data, "longdescription")
	success &= validateStringMap(data, "license", requiredLicenseKeys, requiredLicenseKeys)
	validPlatformList = validateList(data, "platforms", validPlatforms)
	success &= validPlatformList
	success &= validateStringMap(data, "installinstructions", validPlatforms, list(data["platforms"]) if validPlatformList else None)
	success &= validateString(data, "version")
	success &= validateString(data, "author")
	success &= validateInteger(data, "minimumbinaryninjaversion")
	return success

def getCombinationSelection(validList, prompt, maxItems=None):
	if maxItems == None:
		maxItems = len(validList)

	prompt2 = "Enter comma separated list of items> "
	if maxItems == 1:
		prompt2 = "> "
	while True:
		print(prompt)
		for i, item in enumerate(validList):
			print("\t{:>3}: {}".format(i, item))
		items = filter(None, raw_input(prompt2).split(","))
		result = []
		success = True
		for item in items:
			try:
				value = int(item.strip())
			except ValueError:
				print("Couldn't convert {} to integer".format(item))
				success = False
				break
			if value < 0 or value >= len(validList):
				print("{} is not a valid selection".format(value))
				success = False
				break
			else:
				result.append(validList[value])
		if success:
			return result

licenseTypes = {
	"MIT"           : """Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.""",
	"2-Clause BSD"  : """Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:\n\n1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.\n\n2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.\n\nTHIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.""",
	"Apache-2.0"    : """Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at\n\n\thttp://www.apache.org/licenses/LICENSE-2.0\n\nUnless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.""",
	"LGPL-2.0"      : """This library is free software; you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation; either version 2   of the License, or (at your option) any later version.\n\nThis library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.\n\nYou should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA""",
	"LGPL-2.1"      : """This library is free software; you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation; either version 2.1 of the License, or (at your option) any later version.\n\nThis library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.\n\nYou should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA""",
	"LGPL-3.0"      : """This library is free software; you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation; either version 3.0 of the License, or (at your option) any later version.\n\nThis library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.\n\nYou should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA""",
	"GPL-2.0"       : """This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.\n\nThis program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along with this program; if not, see <http://www.gnu.org/licenses/>.""",
	"GPL-3.0"       : """This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.\n\nThis program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>."""
}

def generatepluginmetadata():
	data = {}
	data["pluginmetadataversion"] = 2
	data["name"] = raw_input("Enter plugin name: ")
	data["author"] = raw_input("Enter your name or the name you want this plugin listed under. ")
	data["type"] = getCombinationSelection(validPluginTypes, "Which types of plugin is this? ")
	data["api"] = getCombinationSelection(validApis, "Which api's are supported? ")
	data["description"] = raw_input("Enter a short description of this plugin: ")
	data["longdescription"] = raw_input("Enter a longer description of this plugin: ")
	data["license"] = {}

	licenseTypeNames = ["Other"]
	licenseTypeNames.extend(licenseTypes.keys())
	data["license"]["name"] = getCombinationSelection(licenseTypeNames, "Enter the license type of this plugin:", 1)[0]
	if data["license"]["name"] == "Other":
		data["license"]["name"] = raw_input("Enter License Type: ")
		data["license"]["text"] = raw_input("Enter License Text: ")
	else:
		data["license"]["text"] = licenseTypes[data["license"]["name"]]

	year = datetime.datetime.now().year
	holder = data["author"]

	answer = raw_input("Is this the correct copyrigtht information?\n\tCopyright {year} {holder}\n[Y/n]: ".format(year=year, holder=holder))
	if answer not in ("Y", "y", ""):
		year = raw_input("Enter copyright year: ")
		holder = raw_input("Enter copyright holder: ")

	data["license"]["text"] = "Copyright {year} {holder}\n\n".format(year=year, holder=holder) + data["license"]["text"]
	data["platforms"] = getCombinationSelection(validPlatforms, "Which platforms are supported? ")

	data["installinstructions"] = {}
	for platform in data["platforms"]:
		print("Enter Markdown formatted installation directions for the following platform: ")
		data["installinstructions"][platform] = raw_input("{}: ".format(platform))
	data["version"] = raw_input("Enter the version string for this plugin. ")
	data["minimumbinaryninjaversion"] = int(raw_input("Enter the minimum build number that you've successfully tested this plugin with: "))
	return data

def main():
	parser = argparse.ArgumentParser(description="Generate README.md (and optional LICENSE) from plugin.json metadata")
	parser.add_argument("filename", type=argparse.FileType("r"), help="path to the plugin.json file", default="plugin.json")
	parser.add_argument("-f", "--force", help="will automatically overwrite existing files", action="store_true")
	parser.add_argument("-i", "--interactive", help="interactively generate plugin.json file", action="store_true")
	args = parser.parse_args()

	if args.interactive:
		plugin = generatepluginmetadata()
		pp = pprint.PrettyPrinter(indent=4)
		pp.pprint(plugin)
	else:
		plugin = json.load(args.filename)["plugin"]

	if validateRequiredFields(plugin):
		print("Successfully validated json file")
	else:
		print("Error: json validation failed")
		sys.exit(0)

	outputfile = os.path.join(os.path.dirname(args.filename.name), "README.md")
	licensefile = os.path.join(os.path.dirname(args.filename.name), "LICENSE")

	if not args.force and (os.path.isfile(outputfile) or os.path.isfile(licensefile)):
		print("Cowardly refusing to overwrite an existing license or readme.")
		if args.interactive:
			f, name = tempfile.mkstemp(prefix="plugin", suffix=".json", dir=".")
			print("instead writing to {}".format(name))
			plugin = {"plugin": plugin}
			os.write(f, json.dumps(plugin, sort_keys=True, indent=4))
			os.close(f)
		sys.exit(0)

	if "license" in plugin and "name" in plugin["license"] and "text" in plugin["license"]:
		name = plugin["license"]["name"]
		text = plugin["license"]["text"]
		license = u"""## License
	This plugin is released under a [{name}](LICENSE) license.
	""".format(name=plugin["license"]["name"])
		print("Creating {licensefile}".format(licensefile=licensefile))
		io.open(licensefile,"w",encoding="utf8").write(plugin["license"]["text"])

	elif ("license" in plugin and "name" in plugin["license"]):
		name = plugin["license"]["name"]
		license = u"""## License
		This plugin is released under a {name}] license.
	""".format(name=plugin["license"]["name"])
	else:
		license = ""

	if "installinstructions" in plugin:
		install = "## Installation Instructions"
		for platform in plugin["installinstructions"]:
			install += "\n\n### {}\n\n{}".format(platform, plugin["installinstructions"][platform])

	if "minimumbinaryninjaversion" in plugin:
		minimum = "## Minimum Version\n\nThis plugin requires the following minimum version of Binary Ninja:\n\n"
		minimum += u" * {}\n".format(plugin["minimumbinaryninjaversion"])
		minimum += "\n"
	else:
		minimum = ""

	if "pluginmetadataversion" in plugin:
		metadataVersion = "## Metadata Version\n\n{}\n\n".format(plugin["pluginmetadataversion"])

	if "dependencies" in plugin:
		dependencies = u"## Required Dependencies\n\nThe following dependencies are required for this plugin:\n\n"
		for dependency in plugin["dependencies"]:
			dependencylist = u", ".join(plugin["dependencies"][dependency])
			dependencies += u" * {dependency} - {dependencylist}\n".format(dependency = dependency, dependencylist = dependencylist)
		dependencies += "\n"
	else:
		dependencies = ""

	template = u"""# {PluginName} (v{version})
	Author: **{author}**
	_{description}_
	## Description:
	{longdescription}
	{install}
	{minimum}
	{dependencies}
	{license}
	{metadataVersion}
	""".format(PluginName = plugin["name"], version = plugin["version"],
			author = plugin["author"], description = plugin["description"],
			longdescription = plugin["longdescription"], license = license,
			dependencies = dependencies, minimum = minimum, install = install,
			metadataVersion = metadataVersion)

	print("Writing {outputfile}".format(outputfile=outputfile))
	io.open(outputfile, "w", encoding="utf8").write(template)

if __name__ == "__main__":
	main()