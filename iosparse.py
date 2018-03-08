# cfgFile = open('netcopa/completed_configurations/711.txt')

#port number / legacy vlan / orgin switchname

#validate that voice =/= data

import re
import sys
#ADD
pathin = sys.argv[1]
file = open(pathin, "r")
outputfile = "netcopa/completed_configurations/711-new.txt"
switch = file
gigCount = 0
hostname = ""
hostnameFinal = ""

#exportwriter = csv.writer(csvfile, delimiter=',')
#exportwriter.writerow(['Switch Name', 'Interface', 'Address Pool(VN)', 'Voice Pool(VN)', 'Authentication'])

def switchread(switchtype):
    if switchtype == "gig":
        with open(outputfile, 'a') as csvfile:
            #switch.close()
            filehere = open(pathin, "r")
            s = filehere
            print("os: cisco_ios\nvars:\n  interfaces:")
            for gigLine in s:
                checkgigint = re.compile("(Gi.*0/[1-9][0-9]|Gi.*0/[1-9]|Fa.*0/[1-9][0-9]|Fa*0/[1-9])")
                if checkgigint:
                    matchgigresult = checkgigint.search(gigLine)
                    if matchgigresult:
                        print("    ",matchgigresult.group(0),":\n      name: ", matchgigresult.group(0), "\n      switchport:")

                checkaccessvlan = re.compile("switchport access vlan (.*)")
                if checkaccessvlan:
                    matchaccessresult = checkaccessvlan.search(gigLine)
                    if matchaccessresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        access:\n          vlan: ", matchaccessresult.group(1))

                checkportmoderegex = re.compile("switchport mode access")
                if checkportmoderegex:
                    matchaccessresult = checkportmoderegex.search(gigLine)
                    if matchaccessresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        mode:\n        - access")

                checkvoicevlan = re.compile("switchport voice vlan (.*)")
                if checkvoicevlan:
                    matchvoiceresult = checkvoicevlan.search(gigLine)
                    if matchvoiceresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        voice:\n          vlan: ", matchvoiceresult.group(1))

    if switchtype == "fe":
        with open(outputfile, 'a') as csvfile:
            # exportwriter = csv.writer(csvfile, delimiter=',')
            # exportwriter.writerow(['Switch Name', 'Interface', 'Address Pool(VN)', 'Voice Pool(VN)', 'Authentication'])
            #switch.close()
            filehere = open(pathin, "r")
            s = filehere
            print("os: cisco_ios\nvars:\n  interfaces:")
            for gigLine in s:
                checkgigint = re.compile("(Fa.*0/[1-9][0-9]|Fa.*0/[1-9])")
                if checkgigint:
                    matchgigresult = checkgigint.search(gigLine)
                    if matchgigresult:

                        print("    ", matchgigresult.group(0), ":\n      name: ", matchgigresult.group(0),
                              "\n      switchport:")

                checkaccessvlan = re.compile("switchport access vlan (.*)")
                if checkaccessvlan:
                    matchaccessresult = checkaccessvlan.search(gigLine)
                    if matchaccessresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        access:\n          vlan: ", matchaccessresult.group(1))

                checkportmoderegex = re.compile("switchport mode access")
                if checkportmoderegex:
                    matchaccessresult = checkportmoderegex.search(gigLine)
                    if matchaccessresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        mode:\n        - access")

                checkvoicevlan = re.compile("switchport voice vlan (.*)")
                if checkvoicevlan:
                    matchvoiceresult = checkvoicevlan.search(gigLine)
                    if matchvoiceresult:
                        # print("Here: ", matchgigresult.group(0))
                        print("        voice:\n          vlan: ", matchvoiceresult.group(1))

                checkbadint = re.compile("interface GigabitEthernet0*")
                if checkbadint:
                    matchedbadresult = checkbadint.search(gigLine)
                    if matchedbadresult:
                        break


                    #exportwriter.writerow([hostnameFinal, matchgigresult.group(0), "1", "1", "1"])

for line in switch:
    checkHostName = re.compile("hostname\s*")
    if checkHostName:
        hostnameMatch = re.compile("hostname (.*)")
        matchhostnameresult = hostnameMatch.search(line)
        if matchhostnameresult:
            hostname = hostnameMatch.search(line)
            hostnameFinal = hostname.group(1)

    checkInt = re.compile("(Giga.*.0/.*|Giga*.[1-5]/0/.*)")
    if checkInt:
        matchResult = checkInt.search(line)
        if matchResult:
            gigCount = gigCount + 1

#print(gigCount)
if gigCount > 6:
    switchread("gig")
if gigCount <= 6:
    switchread("fe")


#print(gigCount)
# if gigCount <=4:
#     feSwitch()
# else:
#     gigSwitch()
