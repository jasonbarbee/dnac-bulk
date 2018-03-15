import re
import sys
import os
import glob
from argparse import ArgumentParser
import ntpath

#declerations
parser = ArgumentParser()
parser.add_argument("-p", "--path", dest="incomingpath", help="Open specified path for cfg files")
#parser.add_argument("-AVLO", "--AccessOverride", dest="argAccessOR", help="Set access mode on non-access ports? (True/False)")
args = parser.parse_args()
#accessOR=args.argAccessOR
path=args.incomingpath
hostname = ""
hostnameFinal = ""
gigCount = ""
results=""

def checkInts(interfacelinein, switchtype):
    #take in line to examine, switch type, compare and extract interfaces numbers
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
            #Declare checks for which lines we'd like to capture
            checkInt = re.search("(interface [GF].*.0/.*|interface [GF].*[1-5]/0/.*)",line)
            checkFE = re.search("(interface F.*0/.*|interface F.*[1-5]/0/.*)",line)
            checkAVlan = re.search(".*switchport access vlan (.*)",line)
            checkMode = re.search(".*.switchport mode access",line)
            checkVVlan = re.search(".*switchport voice vlan (.*)",line)
            checkHName = re.search("hostname.* (.*)",line)
            checkTrunk = re.search("int.*G.*.0/(49|50|51|52)|int.*G.*.1/[1-8]",line)
            checkTrunkStack = re.search("interface G.*.[1-5]/0/(49|50|51|52)",line)
            #Preset FastEthernet switch flag
            feSwitch = False
            
            #Is this a trunk port?  No want....
            if checkTrunk:
                break

            #Is this a trunk port on a stack?  Keep reading until we get to next stack!
            if checkTrunkStack:
                checkEndInt = re.search("(interface GigabitEthernet2/0/.*|interface FastEthernet2/0/.*)",line)
                while not checkEndInt:
                    tempLine = fileOpen.readline
                    if (tempLine == ""):
                        break
            #Check for hostname
            if checkHName:
                collectLine += "hostname: "+checkHName.group(1)+"\n   interfaces:"
            #Check interfaces
            if checkInt:
                #If we've detected FE switch, flag it
                if checkFE:
                    feSwitch = True
                #Process interfaces based on switch type
                if feSwitch:
                    collectLine +=checkInts(line, "fe")
                else:
                    collectLine +=checkInts(line, "gig")
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
        #build file output name based on existing config name
        filename_base, file_extension = os.path.splitext(filename)
        finalfile = os.path.dirname(os.path.realpath(__file__))+"/yml_cfgs/"
        ymlfilname = os.path.basename(filename_base)
        #if directory doesn't exist, create it
        if not os.path.exists(os.path.dirname(finalfile)):
            os.makedirs(finalfile)
        #open file for write out
        with open(finalfile+ymlfilname+".yml", "w") as text_file:
            nowantVlans=""
            text_file.write(collectLine)
            print("File : "+finalfile+ymlfilname+".yml created!")
            #output access vlans
            i=0
            while i < len(accessVlans):
                finalVlanOut += accessVlans[i]+","
                i += 1
            print("Access Vlans: "+finalVlanOut.rstrip(','))
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
                if nowantVlans:
                    print("Voice Vlans: "+finalVVlanOut.rstrip(','))
                    print("****Voice Vlans Found In Data Vlans: "+nowantVlans.rstrip(',')+" ****")
        print("\n")
    else:
        print("Please ensure configs are txt or cfg extension!")
