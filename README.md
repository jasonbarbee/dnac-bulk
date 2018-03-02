# DNAC Bulk Provisioning script
Author: Jason Barbee

Contributions by: Jeremy Sanders

Copyright TekLinks, Inc 2018

Latest Version tested DNA 1.1.2

# Features
* Imports CSV to DNA Switch ports
* Exports DNA Switch ports to CSV
* Converts IOS to CSV format for import
* Merges 24 to 48 port switch port in the CSV for combining (2) 24 port switches to a 48.
* Exports Virtual Networks and Address pools. 

# Setup Python for DNAC-Bulk Tools
Install Python 3 and Libraries
```
pip3 install requests pyaml
```

Modify your config.yml file
```
global:
  hostname: 'fqdn_of_DNAC'
  username: 'admin'
  password: 'password'
  defaultVoiceVN: '10_0_1_0-Phone_VN' (your default phone VN)
  VoiceVlans: ['101','102'] (this helps the script know what voice vlans are - must manually update till I use the spreadsheet field.)
```

If you are using Netcopa for conversions, install Python 2.7 and it's requirements.txt file.
on mac that is like this
```
cd netcopa
pip2 install -r requirements.txt
```

## Mapping Vlans to DNA Address Pools via Vlans.csv
This is a format that worked for us, it stores some relevant data as we migrate.

## Note about Netcopa conversions
You do NOT have to use my NetCopa conversion process, you can just build a plain CSV in any way you wish and run the import. The process helps us convert large batches of IOS config files.

# Import a DNA switch via CSV
Have a CSV file ready through conversion(below) or manual building that looks like this
```
Switch Name,Interface,Address Pool(VN),Voice Pool(VN),Authentication
CLOSETSWITCH_1.domain.loc,GigabitEthernet1/0/1,10_0_0_0-Corp_VN,10_0_1_0-Phone_VN,No Authentication
```

```
python3 dnac-bulk.py --action import --input closet1.csv --switchname switch1.domain.loc
```

# Export a DNA Switch Network CSV
It will generate a compatible format above for re-importing. Good for backups.

```
python3 dnac-bulk.py --action export --output export.csv --switchname switch.domain.com
```

# Clear Configs
Wipe switch so that it can be re-provisioned from CLI.

```
python3 dnac-bulk.py --action clear --switchname switch.domain.com 
```

# Conversion Step 1 - Prepare
Credit to netcopa project.
This step will convert text IOS files into a YAML structure that this script will them process.
1. Download Netcopa, and copy my file closet_ios.yml into the netcopa/host_vars folder.
2. Obtain your Cisco IOS config file. 
3. Scrub it of all lines except interfaces and an "end" statement". Remove all show commands, etc.
4. Remove any extra commands like spanning tree, port security, cdp, whatever under the interfaces. Netcopa does not process unexpected input well. .
1. Place cleaned switch config in netcopa/configs.
2. Name it something like 211.cfg
3. Duplicate closet_ios.xml file to match the name like 211.yml in the netcopa/host_vars folder. This fille basically tells Netcopa to use the IOS parser, and gives it a blank structure to fill in.

closet_ios.yml contents
```
os: cisco_ios
vars:
```

# Conversion Step 2 - Running netcopa

``` bash
python2.7 runparse.py
```

This will process all the configs and fill in the vars: field in the .xml file with structured YAML.
Scroll up to see if it was successful. The logs are a little hard to read.
I have several times had to skip problem parsing areas like this. If you have scrubbed your config down to interfaces, this won't be an issue.

``` bash
python2.7 runparse.py --skip logging
```

# Conversion Process - Troubleshooting NETCOPA

*Read the output carefully.*

Look on your screen for buffer like this
``` 
'######## ACTUAL'
[['interface FastEthernet0'],
 ['interface GigabitEthernet0/1',
  ' switchport access vlan 10',
  ' switchport mode access',
  ' switchport voice vlan 20'],

and 
'######## JINJA RESULT'
[['interface FastEthernet0'],
 ['interface GigabitEthernet0/1',
  ' switchport access vlan 10',
  ' switchport mode access',
  ' switchport voice vlan 20'],
```
  Capture the output, and DIFF/Compare them if you need to.

# Conversion - Step 2 - Convert the YML Configurations to DNAC import CSV.

The script will stop when it finds a port hard coded to an access voice vlan. DNA will not let you assign a voice address pool into a data address (access vlan)
They in a list in the config.yml file.

## Running the Conversion
This will conver the YAML to a CSV intermediary format for my script to later import.

```
python3 dnac-bulk.py --action convert --stack 1 --input netcopa/host_vars/211.yml --output 211.csv
```

* Run the Conversion process for Stack 2, etc. It will append to the csv file.

```
python3 dnac-bulk --stack 2 --input 212.yml --output 21.csv 
```

If you need to convert a 24 to 48 port switch use --to48 it will transpse interfaces by 24, useful on the second switch in a merged stack of 48 ports.
```
python3 dnac-bulk --stack 2 --input 212.yml --output 21.csv  --to48
```

# Caveats
* VN/Pool export shows up on screen, it does not write to CSV well yet. Partially implemented.
* I never had to bulk 802.1x yet, we are using no authentication, so the netcopa does not reflect if the port used 802.1x or not. The import process example is for no authentication, but you can change that to any of the expected values in DNA.
* This uses undocumented API calls to DNA, and may be volatile. I am documeting what I use it on. I had to reverse engineer the calls using Firefox Inspector on the DNA Web Interface.
* I plan to support this through a rollout of a few hundred switches probably till late 2018, we'll see where things are at that point. 
* Open a github issue if you have one, or submit a pull request and I'll review it. We have 300 switches or so left to go, so if you think it's useful, I might add it.
* Long term, once Cisco publishes a real DNA API, this tool may become obsolete.

# TODO
* Use filename as the import switchname instead of parameter.
* Remove switch name from CSV.
* Remove the voice vlan markings in config file and use CSV to understand voice vlans
* Simplify CSV formatting.

# Credits
Netcopa Project
https://github.com/cidrblock/netcopa
