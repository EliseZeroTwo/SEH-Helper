''' Python script to generate a stub README.md files from a plugin.json file '''
import json
import argparse
import os
import sys
import io

parser = argparse.ArgumentParser(description = 'Generate README.md (and optional LICENSE) from plugin.json metadata')
parser.add_argument('filename', type = argparse.FileType('r'), help = 'path to the plugin.json file')
parser.add_argument("-f", "--force", help = 'will automatically overwrite existing files', action='store_true')

args = parser.parse_args()

plugin = json.load(args.filename)['plugin']

outputfile = os.path.join(os.path.dirname(args.filename.name), 'README.md')
licensefile = os.path.join(os.path.dirname(args.filename.name), 'LICENSE')

if not args.force and (os.path.isfile(outputfile) or os.path.isfile(licensefile)):
	print("Cowardly refusing to overwrite an existing license or readme.")
	sys.exit(0)

if 'license' in plugin and 'name' in plugin['license'] and 'text' in plugin['license']:
	name = plugin['license']['name']
	text = plugin['license']['text']
	license = u'''## License
This plugin is released under a [{name}](LICENSE) license.
'''.format(name=plugin['license']['name'])
	print("Creating {licensefile}".format(licensefile=licensefile))
	io.open(licensefile,'w',encoding='utf8').write(plugin['license']['text'])

elif ('license' in plugin and 'name' in plugin['license']):
	name = plugin['license']['name']
	license = u'''## License
	This plugin is released under a {name}] license.
'''.format(name=plugin['license']['name'])
else:
	license = ''

if 'minimumBinaryNinjaVersion' in plugin:
	minimum = '## Minimum Version\n\nThis plugin requires the following minimum version of Binary Ninja:\n\n'
	for chan in plugin['minimumBinaryNinjaVersion']:
		version = plugin['minimumBinaryNinjaVersion'][chan]
		minimum += u" * {chan} - {version}\n".format(chan = chan, version = version)
	minimum += '\n'
else:
	minimum = ''

if 'dependencies' in plugin:
	dependencies = u'## Required Dependencies\n\nThe following dependencies are required for this plugin:\n\n'
	for dependency in plugin['dependencies']:
		dependencylist = u', '.join(plugin['dependencies'][dependency])
		dependencies += u" * {dependency} - {dependencylist}\n".format(dependency = dependency, dependencylist = dependencylist)
	dependencies += '\n'
else:
	dependencies = ''

template = u'''# {PluginName} (v{version})
Author: **{author}**
_{description}_
## Description:
{longdescription}
{minimum}
{dependencies}
{license}
'''.format(PluginName = plugin['name'], version = plugin['version'],
		   author = plugin['author'], description = plugin['description'],
		   longdescription = plugin['longdescription'], license = license,
		   dependencies = dependencies, minimum = minimum)

print("Writing {outputfile}".format(outputfile=outputfile))
io.open(outputfile, 'w', encoding='utf8').write(template)

