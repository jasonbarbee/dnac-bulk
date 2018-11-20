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
import glob
from requests.auth import HTTPBasicAuth
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser()
parser.add_argument("--action", "-a", help="set action - import, backup, export, parse, convert, findhost, findphone, vnexport or clear")
parser.add_argument("--input", "-i", help="set input file")
parser.add_argument("--to48","-t", help="Convert 24 port to 48 port")
parser.add_argument("--output", "-o", help="set output file")
parser.add_argument("--delete", "-x", help="clear switch")
parser.add_argument("--switchname", "-n", help="set switchname")
parser.add_argument("--vlanfile", "-v", help="set vlanfile")
parser.add_argument("--stack", "-s", help="set stack number")
parser.add_argument("--debug","-d",help="turn on debugs")
parser.add_argument("--inventory","-inv", help="Print Switch Inventory IP and Status")
parser.add_argument("--securecrt","-crt",help="Print out Secure CRT file of the database")
parser.add_argument("--mac","-f",help="Find MAC address in the network")
parser.add_argument("--inpath", "--path", dest="incomingpath", help="Open specified path for cfg files")
parser.add_argument("--backup", "-b", help="Backup switch port configs from DNA")
parser.add_argument("--backupconfigs", "-bc", help="Backup raw configs from DNA")
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
securecrt_username = cfg['global']['securecrt_username']
securecrt_rootfolder = cfg['global']['securecrt_rootfolder']


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
    if args.action in ['convert','parse','migrate']:
        print("Please Provide an input file with --input (filename.csv)")
    if args.action in ['convert','parse','migrate']:
       if args.incomingpath is None:
            print("Please Provide an input path with --inpath")
else:
    inputfile = args.input
if args.output is None:
    if args.action == 'export':
        print("Assuming output file of export.csv, you can override with --output")
else:
    outputfile = args.output

def authDNAC():
    authURL = 'https://' + dnacFQDN + '/api/system/v1/identitymgmt/login'
    #auth to DNAC
    authResponse = s.get(authURL, auth=HTTPBasicAuth(username, password), verify=False)
    if authResponse.reason == 'Unauthorized':
        print("*** DNA Authentication Failed. Check config.yml for user/password issues.")
        quit()
    else:
       return authResponse.headers['set-cookie'] 

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

def getSwitchLocation(switchName):
    switchUUID = getSwitchUUID(switchName)
    LookupURL = 'https://' + dnacFQDN + '/api/v1/member/group?groupType=SITE&id=' + switchUUID
    Response = s.get(LookupURL, verify=False, headers=reqHeader)
    json=Response.json()
    if args.debug:
        print("DEBUG: API URL", LookupURL)
        print("DEBUG: API Switch Site Response", Response)
    if json['response'] == []:
        print("**** FATAL ERROR ****")
        print("Switch Location Not Found - check the name of the Switch : " + switchName)
        quit()
    else:
        if json['response'][switchUUID] == [{}]:
            return []
        else:
            return json['response'][switchUUID]


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
    if len(jsonSwitchLookup['response']) == 0:
        print("Switch Name " + switchName + " not found!")
        quit()
    return jsonSwitchLookup['response'][0]['id']

def getSwitchName(switchUUID):
    #query for the Switch name mapping to UUID
    switchLookupURL = 'https://' + dnacFQDN + '/api/v1/network-device/?id=' + switchUUID
    switchLookupResponse = s.get(switchLookupURL, verify=False, headers=reqHeader)
    jsonSwitchLookup = switchLookupResponse.json()
    return jsonSwitchLookup['response'][0]['hostname']

def getNetName(segmentUUID):
    #query for the VN name mapping to UUID
    LookupURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/Segment?id=' + segmentUUID
    LookupResponse = s.get(LookupURL, verify=False, headers=reqHeader)
    jsonSwitchLookup = LookupResponse.json()
    if args.debug:
        print("DEBUG: Get NetName URL", LookupURL)
        print("DEBUG: GetNetName Lookup Response", jsonSwitchLookup)
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

def getPhoneList():
    #query for the last 4 of a mac - middle aabb
    LookupURL = 'https://' + dnacFQDN + '/api/v1/host?subType=IP_PHONE'
    LookupResponse = s.get(LookupURL, verify=False, headers=reqHeader)
    jsonLookup = LookupResponse.json()
    if jsonLookup['response'] == []:
        print("No results found")
        quit()
    if len(jsonLookup['response']) < 1:
        if 'errorCode' in jsonLookup['response'].keys():
            if jsonLookup['response']['errorCode'] == 'Bad request':
                print("Error in Querying for MAC Address.")
                quit()
    if args.debug:
        print("DEBUG: Get Lookup MAC URL", LookupURL)
        print("DEBUG: Get Host Lookup Response", LookupResponse)
    return jsonLookup['response']

def importDNAC(switchName):
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
                if row[2] == '':
                    print("*** ERROR *** Missing Data Vlan in CSV")
                dataNetworkUUID=getNetUUID(row[2])
                if dataNetworkUUID == 'NOT FOUND':
                    print("*** ERROR ****")
                    print("DNA Data Fabric Address Pool not Found:", row[2])
                #get voice net uuid
                if row[3] == '':
                    print("*** ERROR *** Missing Voice Vlan in CSV")
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

def clearSwitch(switchName): 
    # This function will clear all interfaces from a given switch.
    print("Clearing Switch to prepare for a fresh import...")
    #add interface to master interface list
    switchUUID = getSwitchUUID(switchName)
    switchData = getDeviceInfo(switchUUID)
    switchIntList = getIntList(switchUUID)
    # Copy the Switch JSON Data
    newSwitchData = switchData.copy()
    # Clear the Interface Array.
    newSwitchData['deviceInterfaceInfo'] = [] 
    # Initialize a variable to rebuild the interfaces.
    oldInterfaceList = []
    for item in switchIntList:
        # Rebuild each interface into the array, but without details.
        oldInterface = {}
        oldInterface['idRef'] = item['id']
        oldInterfaceList.append(oldInterface)
    newSwitchData['deviceInterfaceInfo'] = []
    # The API requires us to push a higher instance Version variable for the object.
    newSwitchData['instanceVersion'] = newSwitchData['instanceVersion']+1
    # Same for the Network Wide Instance Version, we bump that too.
    newSwitchData['networkWideSettings']['instanceVersion'] = newSwitchData['networkWideSettings']['instanceVersion']+1
    # I think this was required also, to stamp the time.
    newSwitchData['lastUpdateTime'] = int(time.time())
    # The Clear configuration did not seem to push this data in it's API call when I compared the web site frontend, so I mirrored it.
    del newSwitchData['customProvisions']
    del newSwitchData['configs']
    del newSwitchData['akcSettingsCfs']
    postData = [newSwitchData]

    updateURL = 'https://' + dnacFQDN + '/api/v2/data/customer-facing-service/DeviceInfo'
            
    updateResponse = s.put(updateURL, data=json.dumps(postData), headers=reqHeader)
    taskId = ''
    if updateResponse.status_code == 202:
        taskId = updateResponse.json()['response']['taskId']
        print("Clear Switch Task was submitted - Task ID ", taskId)
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

def printExport(switchname):
    print("Printing current DNA Config for ", switchname)
    # args.file = "export.csv"
    switchUUID = getSwitchUUID(switchname)
    switchIntList = getIntList(switchUUID)
    switchIntDict = {}
    for item in switchIntList:
        switchIntDict[item['id']] = item['portName']
    switchInfo = getDeviceInfo(switchUUID)
    for item in switchInfo['deviceInterfaceInfo']:
        switchName = getSwitchName(switchUUID)
        intId = item['interfaceId']
        intName = switchIntDict[intId]
        dataNetName = ''
        voiceNetName = ''
        if 'authenticationProfile' in item.keys():
            authProfileName = item['authenticationProfile']['name']
        else:
            authProfileName = 'No Authentication'
        if len(item['segment']) == 2:
            dataNetName = getNetName(item['segment'][0]['idRef'])
            voiceNetName = getNetName(item['segment'][1]['idRef'])
        elif len(item['segment']) == 1:
            dataNetName = getNetName(item['segment'][0]['idRef'])
        print(switchName, intName, authProfileName, dataNetName, voiceNetName)
    print("Exporting Complete")

def exportDNAC(switchname):
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
            dataNetName = ''
            voiceNetName = ''
            if 'authenticationProfile' in item.keys():
                authProfileName = item['authenticationProfile']['name']
            else:
                authProfileName = 'No Authentication'
            if len(item['segment']) == 2:
                dataNetName = getNetName(item['segment'][0]['idRef'])
                voiceNetName = getNetName(item['segment'][1]['idRef'])
            elif len(item['segment']) == 1:
                dataNetName = getNetName(item['segment'][0]['idRef'])
            print(switchName, intName, authProfileName, dataNetName, voiceNetName)
            exportwriter.writerow([switchName, intName, dataNetName, voiceNetName, authProfileName])
    print("Backup Complete")
    quit()

def backupDNAC():
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
    print("Exporting VNs and IP Pools")
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

def convertConfigYML(inpath,outpath):
    for filename in glob.glob(os.path.join(outpath, '*.csv')):
        # Clean up all files in the output folder.
        os.remove(filename)
    for filename in glob.glob(os.path.join(inpath, '*.yml')):
        # read each filename and conver it one by one.
        with open(filename,'r') as cfgfile:
                cfg = yaml.load(cfgfile)
        #build file output name based on existing config name
        filename_base, file_extension = os.path.splitext(filename)
        # Normalize the original filename with the stack key in it.
        filename_base = filename_base.replace("-","_")
        # Grab the stack number from the last _ in the filename
        stack = int(filename_base.split("_").pop())
        newpath = os.path.dirname(os.path.realpath(__file__))+"/"+outpath
        ymlfilename = os.path.basename(filename_base)
        # ymlfilename = ymlfilename.replace("-","_")
        ymlfilename = ymlfilename.split("_")
        # drop the _stack from the filename
        ymlfilename = ymlfilename[:-1]
        # Join yml back together with a _
        ymlfilename = "_".join(ymlfilename)

        # if directory doesn't exist, create it
        # if not os.path.exists(os.path.dirname(newpath)):
        #     os.makedirs(newpath)
        # if stack > 1:
            # Append stacks together
            # mode = 'a'
        # else:
            # Overwrite, remove the old file in case this is a re-run.
            # mode = 'w'
            # # Remove the old file.
            # if os.path.exists(newpath+ymlfilename+".csv"):
            #     os.remove(newpath+ymlfilename+".csv")
        if (stack == 1):
            if os.path.exists(newpath+ymlfilename+".csv"):
                # write header in the top of the file. We found stack 1 file if it exists that means we processed stack 2 first.
                csvfile = open(newpath+"/"+ymlfilename+".csv",'r')
                oldfiledata = csvfile.read()
                csvfile.close()
                csvfile = open(newpath+"/"+ymlfilename+".csv",'w')
                filedata = csvfile.write('Switch Name, Interface, Address Pool(VN), Voice Pool(VN), Authentication')
                filedata = csvfile.write(oldfiledata)
                csvfile.close()
        with open(newpath+"/"+ymlfilename+".csv",'a') as csvfile:
            count = 0
            exportwriter = csv.writer(csvfile, delimiter=',')
            if (stack == 1):
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
                                    newint = re.sub('t0', 't' + str(stack) + '/0', oldint)
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

# IOS Parser
def checkInts(interfacelinein, switchtype):
    #take in line to examine, switch type, compare and extract interfaces numbers
    results=""
    if switchtype == "gig":
        checkgigint = re.search("(G.*0/(?!49|50|51|52)[1-9][0-9]|G.*0/(?!49|50|51|52)[1-9]|F.*0/(?!49|50|51|52)[1-9][0-9]|F*0/(?!49|50|51|52)[1-9])",interfacelinein)
    else:
        checkgigint = re.search("(F.*.0/(?!49|50|51|52)[1-9][0-9]|F.*.0/(?!49|50|51|52)[1-9])",interfacelinein)
    if checkgigint:
        results = "\n    "+checkgigint.group(0)+":\n      name: "+checkgigint.group()+"\n      switchport:\n"
    if results:
        return results
    else:
        return ""

def buildYML(path):
    #Step 1 in the Conversion - take a directory of config files, and convert them to YML.
    hostname = ""
    hostnameFinal = ""
    gigCount = ""
    results=""
    intCount = 0
    lastIntName = ''
    skipInt = False
    for filename in glob.glob(os.path.join(path, '*')):
        if filename.endswith((".cfg", ".txt")):
            finalVlanOut=""
            finalVVlanOut=""
            accessVlans=[]
            voiceVlans=[]
            collectLine ="os: cisco_ios\nvars:\n"
            fileOpen = open(filename,"r")
            currentIntName = ''
            for line in fileOpen:
                #Declare checks for which lines we'd like to capture
                # checkInt matches the config part if show commands are in the file.
                checkInt = re.search("(interface [GF].*.0/.*|interface [GF].*[1-5]/0/.*)",line)
                checkFE = re.search("(F.*0/.*|F.*[1-5]/0/.*)",line)
                checkAVlan = re.search(".*switchport access vlan (.*)",line)
                checkMode = re.search(".*.switchport mode access",line)
                checkModeTrunk = re.search(".*.switchport mode trunk",line)
                checkVVlan = re.search(".*switchport voice vlan (.*)",line)
                checkHName = re.search("hostname.* (.*)",line)
                checkTrunk = re.search("G.*.0/(49|50|51|52)|G.*.1/[1-8]|Port-channel*",line)
                checkTrunkStack = re.search("G.*.[1-5]/0/(49|50|51|52)",line)
                #Preset FastEthernet switch flag
                feSwitch = False
                #Check for hostname
                if checkHName:
                    collectLine += "   hostname: "+checkHName.group(1)+"\n   interfaces:"
                #Is this a trunk port?  No want....
                if checkInt:
                    # We found a new interface, it's time to process it.
                    skipInt = False 
                # If this flag is set, no need to process anything further.
                if skipInt:
                    # Skip lines until we find the next interface.
                    continue
                else:
                    if checkTrunk:
                        # Skip high 49-52 ports, port channels or Gig1/1/1-8 type ports.
                        skipInt = True
                        continue
                    if checkInt:
                        skipInt = False
                        if checkFE:
                            feSwitch = True
                        #Process interfaces based on switch type
                        if feSwitch:
                            currentIntName = line
                            collectLine += checkInts(line, "fe")
                        else:
                            currentIntName = line
                            collectLine += checkInts(line, "gig")
                        intCount = intCount + 1
                    if checkModeTrunk:
                        # It's not an expected uplink. Report the port and quit.
                        print(currentIntName + ": unsupported trunk port. Change to valid access and try again. Skipping Interface")
                        skipInt = True
                                #Check access vlan
                    if checkAVlan:
                        collectLine +="        access:\n          vlan: "+checkAVlan.group(1)+"\n"
                        if checkAVlan.group(1) not in accessVlans:
                            accessVlans.append(checkAVlan.group(1))
                    #Check access mode
                    if checkMode: #or accessOR:
                        collectLine +="        mode:\n        - access"
                    #Check voice vlan
                    if checkVVlan:
                        collectLine +="\n        voice:\n          vlan: "+checkVVlan.group(1)+"\n"
                        if checkVVlan.group(1) not in voiceVlans:
                            voiceVlans.append(checkVVlan.group(1))
                    # Reset the pointer to the last good interface
                lastIntName = currentIntName
                #Is this a trunk port on a stack?  Keep reading until we get to next stack!
                if checkTrunkStack:
                    checkEndInt = re.search("(GigabitEthernet2/0/.*|FastEthernet2/0/.*)",line)
                    # do we need to add more stacks here?
                    while not checkEndInt:
                        tempLine = fileOpen.readline
                        if (tempLine == ""):
                            break

            #build file output name based on existing config name
            filename_base, file_extension = os.path.splitext(filename)
            finalfile = os.path.dirname(os.path.realpath(__file__))+"/yml_cfgs/"
            ymlfilname = os.path.basename(filename_base)
            #if directory doesn't exist, create it
            if not os.path.exists(os.path.dirname(finalfile)):
                os.makedirs(finalfile)
            #open file for write out
            vlanlist = []
            with open(finalfile+ymlfilname+".yml", "w") as text_file:
                nowantVlans=""
                text_file.write(collectLine)
                print("File : yml_cfgs/"+ymlfilname+".yml created!")
                print(str(intCount) + " interfaces found ")
                with open(vlanfile) as vlancsvfile:
                    vlanreader = csv.reader(vlancsvfile, delimiter=',')
                    row = 1
                    for row in vlanreader:
                        vlanlist.append(row[1])
                #output access vlans
                i=0
                notfoundvlans = []
                # while i < len(accessVlans):
                for vlan in accessVlans:
                    finalVlanOut += vlan +","
                    if vlan in vlanlist:
                        pass
                    else:
                        notfoundvlans.append(vlan)
                print("Access Vlans: "+finalVlanOut.rstrip(','))
                if notfoundvlans != []:
                    print("Vlans not found!", notfoundvlans)
                #output voice vlans
                i=0
                if (voiceVlans):
                    while i < len(voiceVlans):
                        finalVVlanOut += voiceVlans[i]+","
                        found = voiceVlans[i] in accessVlans
                        if found:
                            nowantVlans+=voiceVlans[i]+","
                        i += 1
                    #check for duplicate voice/data vlans
                    # this might not be necessary...
                    if nowantVlans:
                        print("Voice Vlans: "+finalVVlanOut.rstrip(','))
                        print("****Voice Vlans Found In Data Vlans: "+nowantVlans.rstrip(',')+" ****")
            print("\n")
        else:
            print("Please ensure configs are txt or cfg extension!")
#IOS Parser


def findHost(mac):
    # Takes a mac aa:bb:cc:dd:ee:ff and locates it in DNA
    print("Searching for Mac Address: ", mac)
    response = lookupHostMac(mac)
    # This should be a singular response.
    print("Host IP: ", response['hostIp'])
    print("Host MAC:", response['hostMac'])
    print("Switch Device IP:", response['connectedNetworkDeviceIpAddress'])
    print("Switch Name:", response['connectedNetworkDeviceName'])
    print("Switch Interface:", response['connectedInterfaceName'])
    quit()

def findPhonePartial(mac):
    # Takes a MAC and searches for a partial match. Strips : from the user input and the responses.
    print("Searching for Phone MAC Addresses ending with ", mac)
    response = getPhoneList()
    mac = mac.lower()
    mac = re.sub(':','',mac)
    for item in response:
        newmac = item['hostMac']
        newmac = newmac.lower()
        newmac = re.sub(':','',newmac)
        if mac in newmac:
            # We found the MAC, break out and print it.
            break
    if mac in newmac:
        print("Host IP: ", item['hostIp'])
        print("Host MAC:", item['hostMac'])
        print("Switch Device IP:", item['connectedNetworkDeviceIpAddress'])
        print("Switch Name:", item['connectedNetworkDeviceName'])
        print("Switch Interface:", item['connectedInterfaceName'])
        quit()
    else:
        print("No matches.")
        quit()

def printInventory():
    switchList = getSwitchList()
    print('{: <30}'.format("Hostname"), '{: <15}'.format("Platform"), '{: ^25}'.format("Uptime"), '{:10}'.format("Version"), '{: ^28}'.format("CollectionStatus"), '{:16}'.format("IP Address"), '{:16}'.format("Reachability"), '{:16}'.format("Status"))
    for switch in switchList:
        switchStatus = switch['inventoryStatusDetail']
        status = re.search(r'''(".*")''', switchStatus).group(0)
        print('{:30}'.format(switch['hostname']),
        '{:15}'.format(switch['platformId'].split(',')[0]),
        '{: ^25}'.format(switch['upTime']),
        '{:10}'.format(switch['softwareVersion']),
        '{: ^28}'.format(switch['collectionStatus']), 
        '{:16}'.format(switch['managementIpAddress']),
        '{:16}'.format(switch['reachabilityStatus']),
        '{:16}'.format(status))
    quit()

def buildSecureCRTFile():
    switchList = getSwitchList()
    with open("securecrt.csv",'w') as csvfile:
        exportwriter = csv.writer(csvfile, delimiter=',')
        exportwriter.writerow(['session_name', 'hostname','protocol','username','folder','emulation'])
        for switch in switchList:
            if switch['role'] == 'DISTRIBUTION':
                prefix = '9500s'
            elif switch['role'] == 'ACCESS':
                prefix = '9300s'
            locationName = getSwitchLocation(switch['hostname'])
            slash = '/'
            if locationName == []:
                locationName = 'Unassigned'
            else:
                locationName = locationName[0]['name']
            folder = securecrt_rootfolder + slash + locationName + slash + prefix
            print("Exporting " + switch['hostname'])
            exportwriter.writerow([switch['hostname'], switch['managementIpAddress'], 'SSH2', securecrt_username, folder, 'XTerm'])
    print("Export to SecureCRT Complete")
    quit()

def downloadConfig(switchUUID,name):
    URL = 'https://' + dnacFQDN + '/api/v1/network-device/' + switchUUID + '/config'
    resp = s.get(URL, verify=False, headers=reqHeader)
    config = resp.json()['response']
    with open('configs/' + name + ".txt", 'wb') as f:  
        f.write(config)
    f.close()

def backupConfigs():
    switchList = getSwitchList()
    for switch in switchList:
        print("Exporting " + switch['hostname'])
        downloadConfig(switch['id'],switch['hostname'])
    print("Export configs Complete")
        
    quit()
# MAIN Program
switchName = args.switchname
# Create Requests Session for API calls
s = requests.Session()
# Define Header variable and scope
reqHeader = {}
#Setup JSON Header for Requests API calls
reqHeader['content-type'] = 'application/json'
# Authenticate to DNA and get a token key
reqHeader['Cookie']  = authDNAC()

if args.action == "import":
    clearSwitch(args.switchname)
    importDNAC(args.switchname)
    printExport(args.switchname)
    quit()
if args.action == "export":
    exportDNAC(args.switchname)
    quit()
if args.action == "backup":
    backupDNAC()
    quit()
if args.action == "convert":
    convertConfigYML(args.incomingpath)
    quit()
if args.action == "parse":
    buildYML(args.incomingpath)
    quit()
if args.action == "migrate":
    buildYML('ios_configs')
    convertConfigYML('yml_cfgs','converted_csvs')
    quit()
if args.action == "clear":
    clearSwitch(args.switchname)
    quit()
if args.action == "vnexport":
    exportVNs()
if args.action == "findhost":
    findHost(args.mac)
    quit()
if args.action == "findphone":
    findPhonePartial(args.mac)
    quit()
if args.action == "inventory":
    printInventory()
    quit()
if args.action == "securecrt":
    buildSecureCRTFile()
    quit()
if args.action == "backupconfigs":
    backupConfigs()
    quit()
else:
    print("Invalid Action please try running --help")
    quit()