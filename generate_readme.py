''' Python script to generate a stub README.md files from a plugin.json file '''
import json
import argparse
import os
import sys

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
	license = '''## License

This plugin is released under a [{name}](LICENSE) license.

'''.format(name=plugin['license']['name'])
	print("Creating {licensefile}".format(licensefile=licensefile))
	open(licensefile,'w').write(plugin['license']['text'])

elif ('license' in plugin and 'name' in plugin['license']):
	name = plugin['license']['name']
	license = '''## License

	This plugin is released under a {name}] license.

'''.format(name=plugin['license']['name'])
else:
	license = ''

if 'minimumBinaryNinjaVersion' in plugin:
	minimum = '## Minimum Version\n\nThis plugin requires the following minimum version of Binary Ninja:\n\n'
	for chan in plugin['minimumBinaryNinjaVersion']:
		version = plugin['minimumBinaryNinjaVersion'][chan]
		minimum += " * {chan} - {version}\n".format(chan = chan, version = version)
	minimum += '\n'
else:
	minimum = ''

if 'dependencies' in plugin:
	dependencies = '## Required Dependencies\n\nThe following dependencies are required for this plugin:\n\n'
	for dependency in plugin['dependencies']:
		dependencylist = ', '.join(plugin['dependencies'][dependency])
		dependencies += " * {dependency} - {dependencylist}\n".format(dependency = dependency, dependencylist = dependencylist)
	dependencies += '\n'
else:
	dependencies = ''

template = '''# {PluginName} (v{version})
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
open(outputfile, 'w').write(template)
