# DNAC Provisioning script
# Author Jason Barbee
# Contributions by: Jeremy Sanders
# Copyright TekLinks, Inc 2018
# DNA 1.1.2

import json
import time
import datetime
import csv
import yaml
import requests
import urllib3
import argparse
import re
import os
from requests.auth import HTTPBasicAuth
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser()
parser.add_argument("--action", "-a", help="set action - import, backup, export, convert, vnexport or clear")
parser.add_argument("--input", "-i", help="set input file")
parser.add_argument("--to48","-t", help="Convert 24 port to 48 port")
parser.add_argument("--output", "-o", help="set output file")
parser.add_argument("--delete", "-x", help="clear switch")
parser.add_argument("--switchname", "-n", help="set switchname")
parser.add_argument("--vlanfile", "-v", help="set vlanfile")
parser.add_argument("--stack", "-s", help="set stack number")
parser.add_argument("--debug","-d",help="turn on debugs")
parser.add_argument("--mac","-f",help="Find MAC address in the network")
vlancsvfile = 'vlans.csv'

# read arguments from the command line
args = parser.parse_args()

# Load the config file
# set variable scope for cfg
cfg = ''
cfgfile = ''
with open('config.yml','r') as cfgfile:
    cfg = yaml.load(cfgfile)

dnacFQDN=cfg['global']['hostname']
username = cfg['global']['username']
password = cfg['global']['password']
defaultVoiceVN = cfg['global']['defaultVoiceVN']
VoiceVlans = cfg['global']['VoiceVlans']

print("DNA Bulk Provisioning Tool. Version 1.0")
print("Author: Jason Barbee with TekLinks, Inc")
print("Github Support URL: https://github.com/jasonbarbee/dnac-bulk ")
print('DNAC host:', dnacFQDN)
print('Default Voice VN:',defaultVoiceVN)
print('If you have Voice Vlans make sure to update config.yml. DNA will not allow access mode voice vlans.')
print('Voice Vlans:', VoiceVlans)
print('-------')
if args.vlanfile is None:
    vlanfile = "vlans.csv"
if args.stack is None:
    if args.action == 'import':
        print("Assuming default stack of 1. You can override this with --stack")
    stack = '1'
else:
    stack = args.stack
if args.input is None:
    if args.action in ['import','convert']:
        print("Please Provide an input file with --input (filename.csv)")
else:
    inputfile = args.input
if args.output is None:
    if args.action == 'export':
        print("Assuming output file of export.csv, you can override with --output")
else:
    outputfile = args.output


switchName = args.switchname
s = requests.Session()
reqHeader = {'content-type': 'application/json'}


def authDNAC():
    authURL = 'https://' + dnacFQDN + '/api/system/v1/identitymgmt/login'
    #auth to DNAC
    authResponse = s.get(authURL, auth=HTTPBasicAuth(username, password), verify=False)
    if authResponse.reason == 'Unauthorized':
        print("*** DNA Authentication Failed. Check config.yml for user/password issues.")
        quit()
    return {'Cookie': authResponse.headers['set-cookie']}

def getNetUUID(netName):
    #query for IP/VN name mapping to UUID
    netLookupURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/Segment?name=' + netName
    netNameResponse = s.get(netLookupURL, verify=False, headers=reqHeader)
    jsonNetName=netNameResponse.json()
    if args.debug:
        print("DEBUG: Get NetUUID URL", netLookupURL)
        print("DEBUG: Get Network UUID Response", netNameResponse)
    if jsonNetName['response'] == []:
        print("**** FATAL ERROR ****")
        print("Network Not Found - check the exact names" + netName)
        quit()
        return 'NOT-FOUND'
    else:
        return jsonNetName['response'][0]['id']

def getIntList(switchUUID):
    #query for the interfame name mapping to UUID
    intLookupURL = 'https://' + dnacFQDN + '/api/v1/interface/network-device/' + switchUUID
    intLookupResponse = s.get(intLookupURL, verify=False, headers=reqHeader)
    jsonIntLookup = intLookupResponse.json()
    if args.debug:
        print("DEBUG: Get IntList URL", intLookupURL)
        print("DEBUG: GetIntList Response", intLookupResponse)
    return jsonIntLookup['response']

def getSwitchList():
    #query for the interfame name mapping to UUID
    LookupURL = 'https://' + dnacFQDN + '/api/v1/network-device'
    LookupResponse = s.get(LookupURL, verify=False, headers=reqHeader)
    jsonLookup = LookupResponse.json()
    if args.debug:
        print("DEBUG: Get Switch List URL", LookupURL)
        print("DEBUG: Swtich List Lookup Response", LookupResponse)
    return jsonLookup['response']

def getSwitchUUID(switchName):
    #query for the Switch name mapping to UUID
    switchLookupURL = 'https://' + dnacFQDN + '/api/v1/network-device/?hostname=' + switchName
    switchLookupResponse = s.get(switchLookupURL, verify=False, headers=reqHeader)
    if args.debug:
        print("DEBUG: Get Switch URL", switchLookupURL)
        print("DEBUG: Swtich Lookup Response", switchLookupResponse)
    jsonSwitchLookup = switchLookupResponse.json()
    return jsonSwitchLookup['response'][0]['id']

def getSwitchName(switchUUID):
    #query for the Switch name mapping to UUID
    switchLookupURL = 'https://' + dnacFQDN + '/api/v1/network-device/?id=' + switchUUID
    switchLookupResponse = s.get(switchLookupURL, verify=False, headers=reqHeader)
    jsonSwitchLookup = switchLookupResponse.json()
    return jsonSwitchLookup['response'][0]['hostname']

def getNetName(segmentUUID):
    #query for the VN name mapping to UUID
    LookupURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/segment?id=' + segmentUUID
    LookupResponse = s.get(LookupURL, verify=False, headers=reqHeader)
    jsonSwitchLookup = LookupResponse.json()
    return jsonSwitchLookup['response'][0]['name']

def getDeviceInfo(switchUUID):
    #query for existing device info
    deviceInfoURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/DeviceInfo?name=' + switchUUID
    deviceInfoResponse = s.get(deviceInfoURL, verify=False, headers=reqHeader)
    jsonDeviceInfo = deviceInfoResponse.json()
    return jsonDeviceInfo['response'][0]

def getVNs():
    URL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/virtualnetworkcontext'
    Response = s.get(URL, verify=False, headers=reqHeader)
    json = Response.json()
    return json['response']

def getIPPools():
    URL = 'https://' + dnacFQDN + '/api/v2/ippool'
    Response = s.get(URL, verify=False, headers=reqHeader)
    json = Response.json()
    return json['response']

def getAuthUUID(authName):
    #query for authentication method UUID
    query = {'namespace': 'authentication', 'name': authName}
    authLookupURL = 'https://' + dnacFQDN + '/api/v1/siteprofile'
    authLookupResponse = s.get(authLookupURL, verify=False, headers=reqHeader, params=query)
    jsonAuthUUID = authLookupResponse.json()
    if jsonAuthUUID == None:
        return None
    else:
        return jsonAuthUUID['response'][0]['siteProfileUuid']

def getTaskStatus(taskId):
    TaskIDURL = 'https://' + dnacFQDN + '/api/v1/task/' + taskId
    taskResponse = s.get(TaskIDURL, verify=False, headers=reqHeader)
    response = []
    for item in taskResponse.json().keys():
        response.append(item.lower())
    if 'response' in response:
        # if 'endTime' in taskResponse.json()['response'].keys():
        #     return taskResponse.json()['response']['endTime']
        if 'errorCode' in taskResponse.json()['response']:
            # If there's an error code, it did not succeed.
            print("Cisco Raw Result:     ", taskResponse.json()['response']['errorCode'] + ':' + taskResponse.json()['response']['failureReason']) 
            if "Invalid idRef" in taskResponse.json()['response']['failureReason']:
                print("**** Recommendation ****")
                print("Are all the DNA address pools assigned into the fabric you are provisioning?")
            if "modify" in taskResponse.json()['response']['failureReason']:
                print("**** Recommendation ****")
                print("Clear the configurtaion on all the ports in DNA and save, and retry.")
            return False
            if 'processcfs_complete' in taskResponse.json()['response'].keys():
                # Sometimes it comes as a nice json formatted complete field.
                return taskResponse.json()['response']['processcfs_complete']
        else:
            # The response comes embedded in the data field, in a ; seperated key value string. I took a shortcut on the indexes. Sorry it's unreadable.
            if taskResponse.json()['response']['data'].split(';')[5].split('=')[1] == 'true':
                return True
            else:
                return None

def lookupHostMac(mac):
    #query for the last 4 of a mac - expects a : in the middle aa:bb
    LookupURL = 'https://' + dnacFQDN + '/api/v1/host?hostMac=' + mac
    LookupResponse = s.get(LookupURL, verify=False, headers=reqHeader)
    jsonLookup = LookupResponse.json()
    if jsonLookup['response'] == []:
        print("No results found")
        quit()
    if 'Bad Request' in jsonLookup['response'][0].keys():
        if jsonLookup['response']['errorCode'] == 'Bad Request':
            print("Error in Querying for MAC Address. Check Formating")
            quit()
    if args.debug:
        print("DEBUG: Get Lookup MAC URL", LookupURL)
        print("DEBUG: Get Host Lookup Response", LookupResponse)
    return jsonLookup['response'][0]

def importDNAC():
    #auth to DNAC and store global cookie variable
    reqHeader['Cookie'] = authDNAC()['Cookie']
    print("*** NOTE: This wipes all configuration and applies this to the switch")
    #init switch list
    switchList = []
    #init interface id
    intUUID=''
    #init auth uuid
    authTypeUUID=''
    #init data net uuid
    dataNetworkUUID=''
    #init voice net uuid
    voiceNetworkUUID=''
    #open CSV and process file
    switchUUID = getSwitchUUID(switchName)
    switchIntList = getIntList(switchUUID)
    with open(args.input) as csvfile:
        switchReader = csv.reader(csvfile, delimiter=',')
        for index, row in enumerate(switchReader, start=0):
            #skip header row
            if index > 0:
                print("Preparing: ", row[1], row[2], row[3], row[4])
                if len(switchList)==0:
                    #if the existing switch list is empty, get the existing device info and add it to the list
                    switchList.append(getDeviceInfo(switchUUID))
                    #clear the interface list (this script is only for whole switch provisioning. It will erase prior configuration)
                    switchList[0]['deviceInterfaceInfo']=[]
                    #set switchMatch to true and store the index of this switch in our switch array
                    switchMatch=[True,0]
                elif len(switchList)>0:
                    #set initial negative match value
                    switchMatch=[False,-1]
                    #loop through switch list to see if our UUID matches one we are already working on
                    for index2, switch in enumerate(switchList, start=0):
                        if switch['name']==switchUUID:
                            #set match to true and store the index number of the matched switch
                            switchMatch=[True,index2]
                    #if no match found append to end of list and store new index
                    if switchMatch[0]==False:
                        switchList.append(getDeviceInfo(switchUUID))
                        switchMatch=[True,len(switchList)-1]
                        #clear the interface list (this script is only for whole switch provisioning. It will erase prior configuration)
                        switchList[0]['deviceInterfaceInfo']=[] 
                    
                #loop through interface collection looking for the matching name
                for index3, iface in enumerate(switchIntList, start=0):
                    if iface['portName']==row[1]:
                        intUUID=iface['id']
                
                #get data net uuid
                dataNetworkUUID=getNetUUID(row[2])
                if dataNetworkUUID == 'NOT FOUND':
                    print("*** ERROR ****")
                    print("DNA Data Fabric Address Pool not Found:", row[2])
                #get voice net uuid
                voiceNetworkUUID=getNetUUID(row[3])
                if dataNetworkUUID == 'NOT FOUND':
                    print("*** ERROR ****")
                    print("DNA Voice Fabric Address Pool not Found:", row[3])
                #get port auth uuid
                authTypeUUID=getAuthUUID(row[4])

                #build interface object
                interface = {
                    "interfaceId": intUUID,
                    "authenticationProfileId": authTypeUUID,
                    "connectedToSubtendedNode": False,
                    "role": "LAN",
                    "segment": [
                        {'idRef': dataNetworkUUID},
                        {'idRef': voiceNetworkUUID}
                    ]
                }
                if args.debug:
                    print("DEBUG: Interface Object", interface)
                #add interface to master interface list
                switchList[switchMatch[1]]['deviceInterfaceInfo'].append(interface)
        if args.debug:
            print("DEBUG - Switchlist object:", switchList)
        updateURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/DeviceInfo'
                
        updateResponse = s.put(updateURL, data=json.dumps(switchList), headers=reqHeader)
        if updateResponse.status_code == 202:
            taskId = updateResponse.json()['response']['taskId']
            print("Provisioning Task was submitted - Task ID ", taskId)
        else:
            print("Provisioning Task Failed to submit. Error code ", updateResponse.status_code)

    # Wait for the task to complete with a valid EndTime.
    task_status = getTaskStatus(taskId)
    while task_status is None:
        print("Waiting for task to complete - this can take 30 seconds to a minute")
        print(time.strftime("%H:%M:%S"))
        time.sleep(3)
        task_status = getTaskStatus(taskId)
    if task_status is True:
        print("Provisioning complete.")
    else:
        print("---------")
        print("Provisioning failed.")
    quit()

def clearSwitch(switchName): 
        #auth to DNAC and store global cookie variable
    reqHeader['Cookie'] = authDNAC()['Cookie']
    #add interface to master interface list
    switchUUID = getSwitchUUID(switchName)
    switchData = getDeviceInfo(switchUUID)
    switchIntList = getIntList(switchUUID)
    newSwitchData = switchData.copy()
    newSwitchData['deviceInterfaceInfo'] = [] 
    oldInterfaceList = []
    for item in switchIntList:
        oldInterface = {}
        oldInterface['idRef'] = item['id']
        oldInterfaceList.append(oldInterface)
    # newSwitchData['deviceInterfaceInfo'] = oldInterfaceList
    newSwitchData['deviceInterfaceInfo'] = []
    newSwitchData['instanceVersion'] = newSwitchData['instanceVersion']+1
    newSwitchData['networkWideSettings']['instanceVersion'] = newSwitchData['networkWideSettings']['instanceVersion']+1
    # newSwitchData['resourceVersion'] = newSwitchData['resourceVersion']+1
    newSwitchData['lastUpdateTime'] = int(time.time())
    del newSwitchData['customProvisions']
    del newSwitchData['configs']
    del newSwitchData['akcSettingsCfs']
    postData = [newSwitchData]

    updateURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/DeviceInfo'
            
    updateResponse = s.put(updateURL, data=json.dumps(postData), headers=reqHeader)
    taskId = ''
    if updateResponse.status_code == 202:
        taskId = updateResponse.json()['response']['taskId']
        print("Clear Switch Task was submitted - Task ID %s", taskId)
    else:
        print("Clear Switch Task Failed to submit. Error code ", updateResponse.status_code)
        quit()

    # Wait for the task to complete with a valid EndTime.
    task_status = getTaskStatus(taskId)
    while task_status is None:
        print("waiting for task to complete - this can take 30 seconds to 1 minute")
        print(time.strftime("%H:%M:%S"))
        time.sleep(5)
        task_status = getTaskStatus(taskId)

    if task_status is True:
        print("Provisioning complete.")
    else:
        print("Provisioning failed.")
    quit()

def exportDNAC(switchname):
        #auth to DNAC and store global cookie variable
    reqHeader['Cookie'] = authDNAC()['Cookie']
    print("Exporting Config for ", switchname)
    # args.file = "export.csv"
    switchUUID = getSwitchUUID(switchname)
    switchIntList = getIntList(switchUUID)
    switchIntDict = {}
    for item in switchIntList:
        switchIntDict[item['id']] = item['portName']
    switchInfo = getDeviceInfo(switchUUID)
    with open(args.output, "w") as csvfile:
        exportwriter = csv.writer(csvfile, delimiter=',')
        exportwriter.writerow(['Switch Name', 'Interface', 'Address Pool(VN)', 'Voice Pool(VN)', 'Authentication'])
        for item in switchInfo['deviceInterfaceInfo']:
            switchName = getSwitchName(switchUUID)
            intId = item['interfaceId']
            intName = switchIntDict[intId]
            authProfileName = item['authenticationProfile']['name']
            dataNetName = getNetName(item['segment'][1]['idRef'])
            voiceNetName = getNetName(item['segment'][0]['idRef'])
            print(switchName, intName, authProfileName, dataNetName, voiceNetName)
            exportwriter.writerow([switchName, intName, dataNetName, voiceNetName, authProfileName])
    quit()

def backupDNAC():
        #auth to DNAC and store global cookie variable
    reqHeader['Cookie'] = authDNAC()['Cookie']
    print("Exporting All DNA Fabric for Default Fabric")
    jsonInventory = getSwitchList()
    with open(args.output, "w") as csvfile:
        exportwriter = csv.writer(csvfile, delimiter=',')
        exportwriter.writerow(['Switch Name', 'Interface', 'Address Pool(VN)', 'Voice Pool(VN)', 'Authentication'])
        for item in jsonInventory:
            switchUUID = item['instanceUuid']
            switchIntList = getIntList(switchUUID)
            switchIntDict = {}
            for item in switchIntList:
                switchIntDict[item['id']] = item['portName']
                switchInfo = getDeviceInfo(switchUUID)
                for item in switchInfo['deviceInterfaceInfo']:
                    switchName = getSwitchName(switchUUID)
                    intId = item['interfaceId']
                    intName = switchIntDict[intId]
                    authProfileName = item['authenticationProfile']['name']
                    dataNetName = getNetName(item['segment'][1]['idRef'])
                    voiceNetName = getNetName(item['segment'][0]['idRef'])
                    print('Exporting ' + switchName)
                    print("switchName, intName, authProfileName, dataNetName, voiceNetName")
                    exportwriter.writerow([switchName, intName, dataNetName, voiceNetName, authProfileName])
    quit()

def exportVNs():
        #auth to DNAC and store global cookie variable
    reqHeader['Cookie'] = authDNAC()['Cookie']
    print("Exporting VNs")
    vnListDict = {}
    poolListDict = {}
    with open(outputfile, "w") as ymlfile:
        print("*** Virtual Networks ***")
        for item in getVNs():
            print(item['name'])
            vnListDict.update({item['name'] : {'vlan' : ''}})
        print("*** IP Pools ***")
        for item in getIPPools():
            print(item['ipPoolName'], item['ipPoolCidr'])
            poolListDict.update({item['ipPoolName'] : {'cidr' : item['ipPoolCidr']}})
        ymldata = dict(vnList = vnListDict, poolList = poolListDict)
        yaml.dump(ymldata, ymlfile, default_flow_style=False)
    quit()

def convertConfigYML(): 
    count = 0
    # read arguments from the command line
    with open(inputfile,'r') as cfgfile:
            cfg = yaml.load(cfgfile)
    with open(outputfile,'a') as csvfile:
        exportwriter = csv.writer(csvfile, delimiter=',')
        if (stack == '1'):
            exportwriter.writerow(['Switch Name', 'Interface', 'Address Pool(VN)', 'Voice Pool(VN)', 'Authentication'])
        interfaces = cfg['vars']['interfaces']
        hostname = cfg['vars']['hostname'] 
        print("Hostname: ", cfg['vars']['hostname'])
        for item in interfaces:
            mode = ''
            accessvlan = ''
            voicevlan = ''
            newint = ''
            dnaVNaccess = ''
            dnaVNvoice = ''
            oldint = interfaces[item]['name']
            # We don't want port channels, management, or vlans, or Gig1 uplink ports. 
            if 'Port-channel' not in oldint:
                if 'FastEthernet0' != oldint:
                    if 'Vlan' not in oldint:
                        if 'GigabitEthernet1' not in oldint:
                            if 'channel_group' in interfaces[item].keys():
                                print('Skipping Port Channel interface ' + oldint)
                            else:
                                count = count + 1
                                if 'mode' in interfaces[item]['switchport'].keys():
                                    mode = interfaces[item]['switchport']['mode'][0]
                                else:
                                    mode = 'trunk'
                                # Rename the interface to the stack number
                                newint = re.sub('t0', 't' + stack + '/0', oldint)
                                newint = re.sub('FastEthernet', 'GigabitEthernet', newint)
                                # If it's a 24 to 48 conversion, bump the interface by 24.
                                if args.to48 == 'true':
                                    oldnumber = re.search(r'0\/(\d+)', newint, re.M|re.I).group(1)
                                    newnumber = str(int(oldnumber) + 24)
                                    newint = re.sub('0/'+ oldnumber,'0/'+ newnumber,newint) 
                                # Grab the access vlan
                                if 'access' in interfaces[item]['switchport'].keys():
                                    accessvlan = interfaces[item]['switchport']['access']['vlan'] 
                                # Grab the voice vlan
                                if 'voice' in interfaces[item]['switchport'].keys():
                                    voicevlan = interfaces[item]['switchport']['voice']['vlan']
                                else:
                                    voicevlan = ''
                                # Open the vlan File to match vlan numbers to DNA Address/VN Segments
                                with open(vlanfile) as vlancsvfile:
                                    vlanreader = csv.reader(vlancsvfile, delimiter=',')
                                    for row in vlanreader:
                                        if row[1] == str(accessvlan):
                                            dnaVNaccess = row[7]
                                            # break -removed. Unsure why I added it.
                                        if str(accessvlan) in VoiceVlans:
                                            print('ERROR ACCESS VOICE VLAN on interface ' + oldint)
                                            print('Processing stopped. Fix the YML source file')
                                            os.remove(outputfile)
                                            quit()
                                        if voicevlan == '':
                                            dnaVNvoice = defaultVoiceVN
                                        else:
                                            if row[1] == str(voicevlan):
                                                dnaVNvoice = row[7]
                                    if dnaVNaccess == '':
                                        print('**** Fatal Error **** ')
                                        print('Error on Port ' + oldint + ', Vlan ' + str(accessvlan) + ' not found. Update vlan.csv file and DNA Appliance.')
                                        quit()
                                print(oldint, mode, accessvlan, voicevlan, '->', newint, dnaVNaccess, dnaVNvoice)
                                exportwriter.writerow([hostname, newint, dnaVNaccess, dnaVNvoice, 'No Authentication'])
        print("Total Interfaces:", count)
        print("Finished conversion")
    quit()

def findHost(mac):
    reqHeader['Cookie'] = authDNAC()['Cookie']
    response = lookupHostMac(mac)
    print("Host IP: ", response['hostIp'])
    print("Host MAC:", response['hostMac'])
    print("Switch Device IP:", response['connectedNetworkDeviceIpAddress'])
    print("Switch Name:", response['connectedNetworkDeviceName'])
    print("Switch Interface:", response['connectedInterfaceName'])
    quit()
# MAIN Program


if args.action == "import":
    importDNAC()
    quit()
if args.action == "export":
    exportDNAC(args.switchname)
    quit()
if args.action == "backup":
    backupDNAC()
    quit()
if args.action == "convert":
    convertConfigYML()
    quit()
if args.action == "clear":
    clearSwitch(args.switchname)
    quit()
if args.action == "vnexport":
    exportVNs()
if args.action == "findhost":
    findHost(args.mac)
    quit()