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
collectLine = ""
results=""


def gethostname(hostline):
        hostnameMatch = re.compile("hostname (.*)")
        matchhostnameresult = hostnameMatch.search(hostline)
        if matchhostnameresult:
            hostname = hostnameMatch.search(line)
            return hostname.group(1)

def checkInts(interfacelinein, switchtype):
    results=""
    if switchtype == "gig":
        checkgigint = re.search("(^interface G.*0/(?!49|50|51|52)[1-9][0-9]|^interface G.*0/[1-9]|^interface F.*0/[1-9][0-9]|^interface F*0/[1-9])",interfacelinein)
    else:
        checkgigint = re.search("(^interface F.*.0/(?!49|50|51|52)[1-9][0-9]|^interface F.*.0/[1-9])",interfacelinein)
    if checkgigint:
        results = "\n    "+checkgigint.group(0)+":\n      name: "+checkgigint.group()+"\n      switchport:\n"

    checkaccessvlan = re.compile(".*.switchport access vlan (.*)")
    if checkaccessvlan:
        matchaccessresult = checkaccessvlan.search(interfacelinein)
        if matchaccessresult:
            results = "        access:\n          vlan: "+matchaccessresult.group(1)+"\n"

    checkportmoderegex = re.compile(".*.switchport mode access")
    if checkportmoderegex:
        matchaccessresult = checkportmoderegex.search(interfacelinein)
        if matchaccessresult:
            results = "        mode:\n        - access"

    checkvoicevlan = re.compile(".*switchport voice vlan (.*)")
    if checkvoicevlan:
        matchvoiceresult = checkvoicevlan.search(interfacelinein)
        if matchvoiceresult:
            results = "\n        voice:\n          vlan: "+matchvoiceresult.group(1)+"\n"
    if results:
        return results
    else:
        return ""



def switchread(switchtype, filepass):
    collectLine ="os: cisco_ios\nvars:\n"
    s = open(filepass, "r")
    filename, file_extension = os.path.splitext(filepass)
    
    if switchtype == "gig":
        for cfgLine in s:
            checkHostName = re.search("hostname.* (.*)",cfgLine)
            if checkHostName:
                collectLine += "hostname: "+checkHostName.group(1)+"\n   interfaces:"
            collectLine +=checkInts(cfgLine, switchtype)

    if switchtype == "fe":
        for cfgLine in s:
            checkHostName = re.search("hostname.* (.*)",cfgLine)
            if checkHostName:
                collectLine += "hostname: "+checkHostName.group(1)+"\n   interfaces:"
            collectLine +=checkInts(cfgLine, switchtype)

    finalfile = os.path.dirname(os.path.realpath(__file__))+"/yml_cfgs/"
    ymlfilname = os.path.basename(filename)
    if not os.path.exists(os.path.dirname(finalfile)):
        os.makedirs(finalfile)
    with open(finalfile+ymlfilname+".yml", "w") as text_file:
        text_file.write(collectLine)
        print("File : "+finalfile+ymlfilname+".yml created!")

for filename in glob.glob(os.path.join(path, '*.cfg')):
    gigCount = 0
    file = open(filename,"r")
    for line in file:
        checkInt = re.search("(Giga.*.0/.*|Giga*.[1-5]/0/.*)",line)
        if checkInt:
            gigCount = gigCount + 1
    if gigCount < 24:
        switchread("fe", filename)
    else:
        switchread("gig", filename)
