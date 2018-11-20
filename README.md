# Cisco DNA Controller SD-Access Bulk Operations 
Author: Jason Barbee

Contributions by: Jeremy Sanders, Heath Kuespert(htothek)

Tested with DNA 1.1.1, 1.1.2, 1.1.4, 1.1.6, 1.1.8, 1.2.5
Latest Version tested DNA 1.2.5

# Features
* Imports CSV to DNA Switch ports
* Exports DNA Switch ports to CSV
* Converts IOS to YML then CSV format for import
* Merges 24 to 48 port switch port in the CSV for combining (2) 24 port switches to a 48.
* Exports Virtual Networks and Address pools. 
* Renames FastEthernet0/XX to GigabitEthernetX/0/XX based on the stack parameter passed.
* Locates a MAC address or any partial mac system wide in DNA.
* Prints Inventory and Provisioning Status of the system
* Exports configs from all devices in DNAC into raw files under configs folder.

# Setup Python for DNAC-Bulk Tools
Install Python 2 (or 3 doesn't matter) and Libraries
```
pip3 install requests pyaml requests
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
## Mapping Vlans to DNA Address Pools via Vlans.csv
This is a format that worked for us, it stores some relevant data as we migrate.

# Parse IOS config to yml structure
This will take a file containg anything along with raw config, turn it into a YAML structure so we can later group the data together into switch stacks for DNA.

Drop your bulk configs in a folder call configs. Use .txt or .cfg suffixes.
Name them like this Closet_1.1_Stack# - like Closet_1.1_1.txt.
If you have Closet_1.1_2.txt the script will join them together automatically as a stack.

## Instructions to Convert IOS directly to DNA import format.
1. Copy configs to configs folder.
2. Run the script below.

```
python3 dnac-bulk.py --action migrate
```
## Migration process:
1. Parses the config folder.
2. Exports to YML in yml_cfg.
3. Cross Lookups DNA reference information to generate import data.
4. Exports CSVs to converted_csvs


# Import a DNA switch via CSV
Have a CSV file ready through conversion(above) or manual building that looks like this
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

# Locate MAC address
```
python3 dnac-bulk.py --action findhost --mac 08:cc:a7:85:cb:5f
```
```
-------
Searching for Phone MAC Addresses ending with 08:cc:a7:85:cb:5f
Host IP:  10.2.2.2
Host MAC: 08:cc:a7:85:cb:5f
Switch Device IP: 10.1.1.1
Switch Name: switch.domain.loc
Switch Interface: GigabitEthernet1/0/48
```

# Backup all configs from all devices in DNAC
```
python3 dnac-bulk.py --action backupconfigs
```
```
-------
Exporting switchname...
```

# Search All IP Phones in DNA by partial MAC
This step uses a DNA API Request to pull all endpoints DNA has categorized as IP_PHONE, and basically greps them for a match.

```
python3 dnac-bulk.py --action findphone --mac cb5f
```
```
-------
Searching for Phone MAC Addresses ending with  cb5f
Host IP:  10.2.2.2
Host MAC: 08:cc:a7:85:cb:5f
Switch Device IP: 10.1.1.1
Switch Name: switch.domain.loc
Switch Interface: GigabitEthernet1/0/48
```
# Print Inventory Status from DNA
```
python3 dnac-bulk.py --action inventory
```

```
Hostname                       Platform                 Uptime           Version          CollectionStatus       IP Address       Reachability     Status
A-DNA-SWITCH                    C9500-40X          95 days, 3:01:50.69    16.6.3               Managed            10.1.1.1        Reachable        "SUCCESS"
```
## Running the Conversion
This will convert the YAML to a CSV intermediary format for my script to later import.

```
python3 dnac-bulk.py --action convert --stack 1 --input yml_cfgs/211.yml --output 211.csv
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
* This uses unofficial API calls to DNA, and may be volatile, but has not been so far(ok - one time they changed an API key), but I follow the WEB UI's response. This is not doing anything more magic than the same API calls you use when in Firefox. I just had to reverse engineer the calls using Firefox Inspector on the DNA Web Interface.
* I plan to actively support this through a rollout of a few hundred more switches probably till end of 2018.
* Open a github issue if you have one, or submit a pull request and I'll review it. We have 300 switches or so left to go, so if you think it's useful, I might add it.
* Long term, once Cisco publishes a real DNA API, I don't know what will happen to this tool.

# Likely roadmap
* Better documentation
* Rethink the way voice address pools are handled.

# License
MIT License.
Copyright Jason Barbee 2018.

# Want Professional DNA / SD-Access Assistance?
C Spire is a Cisco Gold Partner that offers professional services to support your DNA SD-Access design and installation.

Visit www.cspire.com for more information
