#validate that voice =/= data

import re
import sys
import os
import glob
from argparse import ArgumentParser
import ntpath

parser = ArgumentParser()
parser.add_argument("-p", "--path", dest="incomingpath", help="Open specified path for cfg files")
args = parser.parse_args()
path=args.incomingpath
hostname = ""
hostnameFinal = ""
gigCount = ""
results=""


def checkInts(interfacelinein, switchtype):
    results=""
    if switchtype == "gig":
        checkgigint = re.search("(^interface G.*0/(?!49|50|51|52)[1-9][0-9]|^interface G.*0/(?!49|50|51|52)[1-9]|^interface F.*0/(?!49|50|51|52)[1-9][0-9]|^interface F*0/(?!49|50|51|52)[1-9])",interfacelinein)
    else:
        checkgigint = re.search("(^interface F.*.0/(?!49|50|51|52)[1-9][0-9]|^interface F.*.0/(?!49|50|51|52)[1-9])",interfacelinein)
    if checkgigint:
        results = "\n    "+checkgigint.group(0)+":\n      name: "+checkgigint.group()+"\n      switchport:\n"
    if results:
        return results
    else:
        return ""

for filename in glob.glob(os.path.join(path, '*')):
    if filename.endswith((".cfg", ".txt")):
        finalVlanOut=""
        finalVVlanOut=""
        accessVlans=[]
        voiceVlans=[]
        collectLine ="os: cisco_ios\nvars:\n"
        fileOpen = open(filename,"r")
        for line in fileOpen:
            checkInt = re.search("(interface [GF].*.0/.*|interface [GF].*[1-5]/0/.*)",line)
            checkFE = re.search("(interface F.*0/.*|interface F.*[1-5]/0/.*)",line)
            checkAVlan = re.search(".*switchport access vlan (.*)",line)
            checkMode = re.search(".*.switchport mode access",line)
            checkVVlan = re.search(".*switchport voice vlan (.*)",line)
            checkHName = re.search("hostname.* (.*)",line)
            checkTrunk = re.search("interface GigabitEthernet0/(49|50|51|52)",line)
            checkTrunkStack = re.search("interface GigabitEthernet1/0/(49|50|51|52)",line)

            if checkTrunk:
                break

            if checkTrunkStack:
                checkEndInt = re.search("interface GigabitEthernet2/0/.*",line)
                while not checkEndInt:
                    tempLine = fileOpen.readline
                    if (tempLine == ""):
                        break

            feSwitch = False

            if checkHName:
                collectLine += "hostname: "+checkHName.group(1)+"\n   interfaces:"

            if checkInt:
                if checkFE:
                    feSwitch = True

                if feSwitch:
                    collectLine +=checkInts(line, "fe")
                else:
                    collectLine +=checkInts(line, "gig")
            
            if checkAVlan:
                collectLine +="        access:\n          vlan: "+checkAVlan.group(1)+"\n"
                if checkAVlan.group(1) not in accessVlans:
                    accessVlans.append(checkAVlan.group(1))
            if checkMode:
                collectLine +="        mode:\n        - access"

            if checkVVlan:
                collectLine +="\n        voice:\n          vlan: "+checkVVlan.group(1)+"\n"
                if checkVVlan.group(1) not in voiceVlans:
                    voiceVlans.append(checkVVlan.group(1))
        
        filename_base, file_extension = os.path.splitext(filename)
        finalfile = os.path.dirname(os.path.realpath(__file__))+"/yml_cfgs/"
        ymlfilname = os.path.basename(filename_base)
        if not os.path.exists(os.path.dirname(finalfile)):
            os.makedirs(finalfile)
        with open(finalfile+ymlfilname+".yml", "w") as text_file:
            text_file.write(collectLine)
            print("File : "+finalfile+ymlfilname+".yml created!")
            i=0
            while i < len(accessVlans):
                finalVlanOut += accessVlans[i]+","
                i += 1
            print("Access Vlans: "+finalVlanOut.rstrip(','))
            i=0
            if (voiceVlans):
                while i < len(voiceVlans):
                    finalVVlanOut += voiceVlans[i]+","
                    i += 1
                print("Voice Vlans: "+finalVVlanOut.rstrip(','))
        print("\n")
            
            

    else:
        print("Please ensure configs are txt or cfg extension!")
