
import os
import subprocess
import shutil
import sys
import json
import stat



DATA_FILE_NAME =  "connectData.json"
FILE_NAME = "connect"
PYFILE = "connect.py"

FOLDER_NAME = "connectivity"

DEFAULT_SUBNET = "255.255.248.0"
DEFAULT_NETWORK = "192.168.216.0"
DEFAULT_GATEWAY = "192.168.17.125"
DEFAULT_DEVICES = {
    "CPU" : "216.101",
    "HS"  : "218.101",
    "STSX": "219.101",
    "STDX": "220.101"
}

DEFAULT_CENTER = "server"


mainCommands = {
    "pipInstall" : "sudo apt install python3-pip",
    "routeDownload": "sudo apt-get install net-tools",
    "update" : "sudo apt update",
    "findPython" : "which python3",
    "routeTable" : "route",
    "sshpassInstall" : "sudo apt-get install sshpass"
 
}

latestConnection = []
toConnect = False

CONNECT_JSON = f"/home/{os.getlogin()}/{FOLDER_NAME}/"


globalPath = "/usr/local/bin"
installed = False
comp = False

data_exists = os.path.exists(globalPath+"/"+DATA_FILE_NAME)
file_exists = os.path.exists(globalPath+"/"+FILE_NAME)

curr = os.path.exists("./"+DATA_FILE_NAME)

args = sys.argv


def proccessWithResult(command):
    res = subprocess.run(command, shell=True, capture_output=True, check=True)
    return res.stdout.decode("utf-8")


def pyModulesInstallation(pyModules):

    for module in pyModules:
        command = f"pip install {module}"
        res = subprocess.run(command, shell=True,capture_output=True, check=True)
        print(f"\n INSTALLED {module}")


def isSCP(value):
    for arg in value:
        if("/" in arg or "\\" in arg):
            return True
        
    return False


def readFile(path):
   
    f = open(path, "r")
    txt = ""
    if(".json" in path):
        f = open(path)
        r = f.read()
        txt = json.loads(r)
        f.close()
        return txt
    
    txt = f.read()
    f.close()
    return txt



def writeFile(path, arg):
   
    if(".json" in path):
        with open(path, "w") as file:
            json.dump(arg, file)
    else:
        f = open(path, "w")
        f.write(arg)
        f.close()

def getDomain(gateway):
    
    res = subprocess.run(f"nslookup {gateway}", shell=True, capture_output=True)
    if(res.returncode != 0):
        return "N/D"
    params = res.stdout.decode("utf-8").split("\t")
    
    for name in params:
        if "name" in name:
            domain = name.split("= ")[1]
            domain = domain.split("\n")[0] 
            domain = domain.split(".")[0]
            return domain
    
    

    

def updateCenterData(data, gateway, mask, name):
    centers = data['servers']

    if(len(name) == 0):
        name = DEFAULT_CENTER+str(len(centers))

    centers[gateway] = {
        "value":name,
        "mask": mask,
        "domain" : getDomain(gateway),
        "connected": {}
    }

    #4 devices connected

    devices = {}
    
    for name, ip in DEFAULT_DEVICES.items():
        ip = ip.split(".")[0]+"."+data['lastPart']
        ip = rebuild(DEFAULT_GATEWAY, ip)
        devices[ip] = name

    centers[gateway]['connected'] = devices

    data['servers'] = centers

    return data 



def readRoutes():
    connectData = {
        "routeData" : [],
        "users" : ["ale", "root"],
        "ssh" : 0,
        "port":22,
        "pswd" : "ale",
        "lastPart" : "101",
        "servers" : {}
        
    }     

    #creating / opening json file 

    routeInfo = proccessWithResult(mainCommands["routeTable"])
    routeInfo = routeInfo.split("\n")

   

    #retrieving the route table

    for i in range(2,len(routeInfo)-1):
        row = routeInfo[i].split(" ")
        dataRow = []

        count = 0

        for j in row:

            if(count == 3):
                break

            if(j != ""):
                dataRow.append(j)
                count+=1
        
        connectData['routeData'].append(dataRow)

    return connectData

def getValue(x):
    if(args[x+1][0] != '-' and x < len(args)):
            return args[x+1]
    
    return ""
            
def rebuild(full, short):
    full= full.split(".")
    short = short.split(".")

    minVal = min(len(short), len(full))

    for i in range(1, minVal+1):
        x = i*-1
        if(len(short[x]) > 0):
            full[x] = short[x]
        else:
            break

    return ".".join(full)



def showCenters(data):
    
    print("\n\n ---------------------- CONQUEROR SERVERS AVAILABLE ---------------\n")
    keys = list(data.keys())

    for key in keys :

        centerName = data[key]['value']

        print(f"\n\n ---------------------- {centerName} -----------------\n")
        print(" value (gateway): ", key)
        print(" domain : ", data[key]['domain'])
        print(" subnet (mask): ", data[key]['mask'])
        

        
        print("",len(data[key]["connected"]),"device connected : ")
        

        devices = list(data[key]["connected"].keys())
        
        for device in devices:
            print("\n",data[key]['connected'][device], " : ", device )
    

def showRouteTable():
    print("\n\nROUTE TABLE UPDATED!")
    route = proccessWithResult(mainCommands['routeTable'])
    print(route)


def addRoute(dest, gw, mask):
    command = f"sudo route add -net {dest} netmask {mask} gw {gw}"
    res = subprocess.run(command, shell=True, capture_output=True, text=True)
   
    if(res.returncode != 0 and "file exists" not in res.stderr.lower()):
        print(f"\033[1;31m 302 add {res.stderr}  {dest} {gw} {mask}")
        sys.exit()
    

def deleteRoute(dest, gw, mask):
    command = f"sudo route delete -net {dest} netmask {mask} gw {gw}"
    res = subprocess.run(command, shell=True, capture_output=True)
    if(res.returncode != 0):
        
        sys.exit()
    




def changeNames(old, new, data):


    names = list(data.keys())
   
    for name in names:
        if(data[name]["value"] == old):
            if(uniqueName(data, new, 0)):
                data[name]["value"] = new
                break
            else:
                return data
    
   

    return data

def moveTo(device, oldCenter, newCenter, data):
    table = data['routeData']
    centers = data['centers']

    detailsToDel = []
    detailsToAdd = []


    for key, values in centers.items():
        found  = False
        if values['value'] == oldCenter:
           
            connected = values['connected']

            for k, v in connected.items():
                if v['value'] == device:
                    detailsToDel.append(k)
                    detailsToDel.append(key)
                    detailsToDel.append(v['mask'])
                    found = True
                    break

            if(found):
                break
        
   
    
    for key, values in centers.items():
        if values['value'] == newCenter:
           
            detailsToAdd.append(detailsToDel[0])
            detailsToAdd.append(key)
            detailsToAdd.append(detailsToDel[2])
            break
    

    if(len(detailsToDel) == len(detailsToAdd) and len(detailsToAdd) == 3):
        
        deleteRoute(detailsToDel[0], detailsToDel[1], detailsToDel[2])
        addRoute(detailsToAdd[0], detailsToAdd[1], detailsToAdd[2])

    #data = updateCenterData(data)
    
    


def argNameCheck(start, end):
    val = []
    start+=1
    if((end+start-1) < len(args)):
        if(args[start][0] != "-" and args[end+start-1][0] != '-'):
            for i in range(start, end+start):
                val.append(args[i])
     
    return val

def combineArgs(start):
    val = []
    start+=1
    for i in range(start, len(args)):
        if(args[i][0] != '-'):
            val.append(args[i])
        else:
            break
     
    return val


def removeDevice(device, center, data):
    table = data['routeData']
    centers = data['centers']

    details = []
    #remove from centers

    found = False
    for center in centers:
        connected = centers[center]['connected']
        
        
        for key, value in connected.items():
            if value['value'] == device :
                details.append(key)
                details.append(center)
                details.append(value['mask'])
                found = True
                del centers[center]['connected'][key]
                break

        if(found) : 
            break

    

    
    #remove from json table

    table.remove(details)

    #remove from the system

    deleteRoute(details[0], details[1], details[2])

    return data


def findCenter(device, data):
    centers = data
    found = []
    for key, value in centers.items():
        
        connected = value['connected']

        for k, v in connected.items():
            if v['value'] == device:
                found.append(key)

    if(len(found) == 1):
        return found[0]
    
    return ""



    
            


def addOrReplace(values, data):
    #values = [dest, mask]
    found = False
    for i in range(len(data)):
        row = data[i]

       
        if(row[0] == values[0] and row[2] == values[2]):
            #rebuild
            print("\n\nFOUND AN EXISTING ROUTE!")

            

            deleteRoute(row[0], row[1], row[2])
            print("\nREPLACING THE ROUTE ...")
            addRoute(values[0], values[1], values[2])

            row[0] = values[0]
            row[1] = values[1]
            row[2] = values[2]

            found = True
            break


    if(not found):
        print("\n\nADDING ROUTE ...")
        addRoute(values[0], values[1], values[2])

        newRow = [values[0], values[1], values[2]]
        data.append(newRow)

    
    return data

def integerCheck(value):
    if("." in value):
        value = value.split(".")

        for i in value:
            if not i.isdigit():
                return False
    else:
        if not value.isdigit():
            return False
        
    return True 




def isIP(value):
    if("." in value):
        #might be an ip
        value = value.split(".")
        digits = 0
        for val in value:
            if(val.isdigit()):
                digits+=1

        if((digits == len(value) or digits == len(value)-1) and len(value)-1 != 0):
            return True

    
    else:
        if(value.isdigit()):
            return True
        
    return False

def getServer(servers, servername):
    
   
    
    for gateway, name in servers.items():
        if(name['value'] == servername):
            return gateway
        
def getDevice(devices, devicename):
    
    for ip, name in devices.items():
        if(name == devicename):
            return ip
        

def serverExists(servers, servername):
    
    if(not isIP(servername)):
        for gateway, value in servers.items():
            if(value['value'] == servername):
                return True
    else:
        if(servername in list(servers.keys())):
            return True
    return False

def deviceExists(servers, devicename, servername):
    
    ser = ""
    for gateway, value in servers.items():
        if(value['value'] == servername):
            ser = gateway
            break
    
    devices = servers[ser]['connected']

    for ip, name in devices.items() :
        if(name == devicename):
            return True
    return False

def showInstructions():
    msg = """
        \n ------------- CONNECT COMMANDS -------------\n\n
        
        DEFAULT_GATEWAY is 192.168.17.125  ---> so if specifing the ip anywhere in command, can use short form (105 ---> 192.168.17.105, or 16.193 ---> 192.168.16.193)\n\n
        DEFAULT_SUBNET is 255.255.248.0  ---> so if specifing the mask anywhere in command, can use short form (255.0 ---> 255.255.255.0)\n\n\n
        
        connect -help ---> (show the instructions)
        connect -s ---> (this command will show the available conqueror servers)\n\n
        connect -to <servername> <devicename> ---> (devicename can be : cpu, hs, stsx, stdx. use servername if server is available with -s command)\n\n
        connect -to <ip / domain> <devicename>  ---> (use ip, ex. 105 or 16.193, or domain, ex QW-SRV-NATIVE01 or QL-ASERPINI IF SERVER IS NOT AVAILABLE in the list )\n\n
        connect -to <ip/domain> <devicename> <servername> ---> (servername will give a personalized name to the server if it's not available in the list)\n\n
        connect -to <ip/domain> <devicename> <subnet> <servername> ---> (subnet will provide a personalized subnet, input ex. 255.0 or 248.0 or 252.0 etc)\n\n
        connect -to <serevername/ip/domain> <localfile> <devicename>:<remotefile> ---> (will send the file to the remote device and connect with ssh)\n\n
        connect -to <serevername/ip/domain> fol <localfolder/file> <devicename>:<remotefile> ---> (use fol if want to send a folder)\n\n
        connect -send <serevername/ip/domain> <localfile> <devicename>:<remotefile> ---> (will only send the file to the remote device)\n\n
        connect -send <serevername/ip/domain> fol <localfile> <devicename>:<remotefile> ---> (use fol if want to send a folder)\n\n
        connect -del <servername/domain/ip> ---> (this will delete a server from the -s list)\n\n
        connect -newname <old servername> <new servername> ---> (change the name of the server)\n\n
        connect -devip <new device ip> ---> (for ex. connect -devip 105, from this point all the new servers will have devices with the ending 105, ex. cpu : 192.168.216:105 instead of 192.168.216:101)\n\n
        connect -to <servername> -devip <new device ip> ---> (change the ip of device of an existing server)\n\n
        connect -to <servername> <devicename> -devip <new device ip> ---> (change and connect to device with new ip)\n\n
        connect -p <new port> ---> (will change the ssh port, DEFAULT IS 22)\n\n
        connect -r ---> (show the route table)\n\n
        connect -uninstall ---> (uninstall connect from the system)
        
        
        
    """
    print(msg)

def networkExists(routes):
    for route in routes:
        if(DEFAULT_NETWORK in route):
            return True
        
    return False
def insert(data, value, installing):
        data['routeData']=readRoutes()['routeData']
    #the gateway provided is an ip
        global latestConnection,toConnect
        ip = rebuild(DEFAULT_GATEWAY, value[0])
        value[0] = ip
        value[2] = rebuild(DEFAULT_SUBNET, value[2])
       
        #check if the gateway already exists
        
        gateways = list(data['servers'].keys())
        
        if(ip in gateways):
            
            dev = getDevice(data['servers'][value[0]]["connected"], value[1])
            if(dev == None):
                print(f"\033[1;31m devicename ({value[1]}) doesn't exists\n")
                sys.exit()
            
            #adjuts the routetable
            value[1] = getDevice(data['servers'][ip]['connected'], value[1])
            
            data['routeData'] = readRoutes()['routeData']
            adjustRouteTable(data, value)
            
            if(installing != 0):
                latestConnection = []
                toConnect = True
                latestConnection.append(value[1])
                latestConnection.append(data['users'])
                latestConnection.append(data['port'])
                latestConnection.append(value[0])
                latestConnection.append(data['pswd'])
                
                #sshConnect(value[1], data['users'], data['port'], value[0], data['pswd'])
           
            
        else:

            #check if network is reachable
            
            networkFound = networkExists(data['routeData'])
            addRoute(DEFAULT_NETWORK, ip, value[2])
            #if everything ok, then network is reachable, 
            #delete it if 192.168.216.0 is already in route table
            if(networkFound):
                deleteRoute(DEFAULT_NETWORK, ip, value[2])
            
            #check the uniqueness of the server name
            
            if(len(value[3]) > 0):
                if(serverExists(data['servers'],value[3])):
                    print(f"\033[1;31m SERVERNAME ({value[3]}) already exists\n")
                    sys.exit()
            
            
            data = updateCenterData(data, ip, value[2], value[3])
            
            #once inserted it will connect
            
            value[1] = getDevice(data['servers'][value[0]]['connected'], value[1])
            
            #adjust routes
            adjustRouteTable(data, value)
            if(installing != 0):
                latestConnection = []
                toConnect = True
                latestConnection.append(value[1])
                latestConnection.append(data['users'])
                latestConnection.append(data['port'])
                latestConnection.append(value[0])
                latestConnection.append(data['pswd'])
                #sshConnect(value[1], data['users'], data['port'], value[0], data['pswd'])
        return data
    
def getAddress(domain):
    
    if("." in domain):
        domain = domain.split(".")[0]
        
    try:
        details = subprocess.run(f"nslookup {domain}", shell=True, capture_output=True)
        details = details.stdout.decode("utf-8").split("\n")
        
        for val in details:
            if(len(val) > 0 and " " in val):
                value = val.split(" ")
                if(value[0] == "Address:"):
                    return value[1]
    except :
        ""

    return "none"


def getPrefix(subnet):
    masks = subnet.split(".")
    ones = 0
    default = 8
    for val in masks:
        
        if(val != "0"):
            while(int(float(val))%2 == 0):
                default-=1
                val = str(int(float(val))/2)
        else:
            default = 0
            
        ones+=default
        
    return ones
        

def adjustRouteTable(data, value):
    table = data['routeData']
    

    found = 0 #how many 192.168.168.0 found
    
    for row in table:
        if(row[0] == DEFAULT_NETWORK and found == 0):
            found+=1
        elif(row[0] == DEFAULT_NETWORK):
            #remove all the paths
            
            if(not isIP(row[1])):
                row[1] = getAddress(row[1])
                
           
            deleteRoute(row[0], row[1], row[2])
            
    if(found != 0):  #replace if there is at least one route availabel
        #replace the remaining one 
        prefix = getPrefix(value[2])
        res = subprocess.run(f"sudo ip route change {DEFAULT_NETWORK}/{prefix} via {value[0]}", shell=True,  capture_output=True)
        if(res.returncode != 0):
            print(f"\033[1;31m {res.stderr}\n")
            sys.exit()
    else:
        addRoute(DEFAULT_NETWORK, value[0], value[2])
        
        
def sshConnect(dest, users, port, server, pswd):
    user = users[0]
    if("218" in dest):
        user = users[1]
    
    print(f"\n\nconnecting :  ssh {user}@{dest} -p {port}")
    print("server : ",server)
    res = subprocess.run(f"ssh {user}@{dest}", shell=True, check=True)
    if(res.returncode != 0):
        sys.exit()
    
        
def deleteServer(servers, servername):
    
  
    if(not isIP(servername)):
        for gateway, val in servers.items():
            if(val['value'] == servername):
                del servers[gateway]
                break
    else:
        del servers[servername]
        
    
    print(F"\n SUCCESSFULLY DELETED {servername}")
    return data['servers']

def replaceValues(servers, servername, lastPart): #replace the devices ips

    if(not isIP(servername)):
        for gateway, value in servers.items():
            if(value['value'] == servername):
                #replace the values
                
                connected = value['connected']
                
                for ip in list(connected.keys()):
                  
                    connected[ip.split(".")[0]+"."+ip.split(".")[1]+"."+ip.split(".")[2]+"."+lastPart] = connected.pop(ip)
                    
                break
    else:
        
        connected = servers[servername]['connected']
        for ip in list(connected.keys()):
            connected[ip.split(".")[0]+"."+ip.split(".")[1]+"."+ip.split(".")[2]+"."+lastPart] = connected.pop(ip)
         
    return servers


def changeName(servers, old, new):
    
    for gateway, name in servers.items():
        if(name['value'] == old):
            name['value'] = new
            break
        
    return servers

def folTrans(value):
    for arg in value:
        if(arg.lower() == "fol"):
            return True
    return False

def valueGenerator(value):
    devicename = value[2].split(":")[0].upper()
    if(len(value) == 4):
        devicename = value[3].split(":")[0].upper()
  
    ip = value[0]
    
    if(not isIP(ip)):
        ip = getAddress(ip)
        if(ip == "none"):
            ip = getServer(data['servers'], value[0])
            if(ip != None):
            #might be the name of a server
                value[0] = ip
   
            else:
                print(f"\033[1;31m servername ({value[0]}) IS NOT CORRECT\n")
                sys.exit()
        else:
            
            value[0] = ip
    else:
        ip = rebuild(DEFAULT_GATEWAY, ip)
        
    value[0] = ip
    
    return [value[0], devicename, DEFAULT_SUBNET, ""]
    
def sendFiles(value, data):
    #scp functionality
    devicename = value[2].split(":")[0].upper()
    if(len(value) == 4):
        devicename = value[3].split(":")[0].upper()
    
    
    ip = value[0]
    dest = ""
    if(not isIP(ip)):
        ip = getAddress(ip)
        if(ip == "none"):
            ip = getServer(data['servers'], value[0])
            if(ip != None):
            #might be the name of a server
                value[0] = ip
   
            else:
                print(f"\033[1;31m servername ({value[0]}) IS NOT CORRECT\n")
                sys.exit()
        else:
            
            value[0] = ip
    else:
        ip = rebuild(DEFAULT_GATEWAY, ip)
        
    value[0] = ip
    dev = getDevice(data['servers'][ip]['connected'], devicename)
    
    if(dev != None):
        dest = dev
    else:
        print(f"\033[1;31m devicename ({devicename}) IS NOT CORRECT : SCP TRANSFER\n")
        sys.exit()
        
    localFile = value[1]
    remoteFile = ""
    try:
        remoteFile = value[2].split(":")[1]
    except:
        ""

    if(len(value) == 4):
        localFile = "-r "+value[2]
        remoteFile = value[3].split(":")[1]
    
    
    user = data['users'][0]
    
    if("218" in dest):
        user = data['users'][1]
    
    if(localFile.lower() == "fol"):
        localFile = "-r"
    res = subprocess.run(f"scp {localFile} {user}@{dest}:{remoteFile}", shell=True, check=True)
    if(res.returncode != 0):
        print(f"\033[1;31m SOMETHING WENT WRONG\n")
        sys.exit()
        
    values = [value[0], devicename, DEFAULT_SUBNET, ""]
    return values
        
def uninstall():
    choise = input("do you want to continue with uninstallation [y/n] : ")
    if(choise.lower() == "y"):
        subprocess.run(f"sudo rm -r /home/{os.getlogin()}/{FOLDER_NAME}", shell=True, capture_output=True)
        
        subprocess.run(f"sudo rm {globalPath}/{DATA_FILE_NAME}", shell=True, capture_output=True)
        subprocess.run(f"sudo rm {globalPath}/{FILE_NAME}", shell=True, capture_output=True)
    
        
        print("SUCCESSFULLY REMOVED CONNECT")
        sys.exit()
    else:
        print("CANCELED THE UNINSTALLATION PROCESS")
    

def connecter(value,data, installing):
    data['routeData']=readRoutes()['routeData']
    global latestConnection,toConnect
    value[0] = value[0].lower()
    value[1] = value[1].upper()
    value[2] = value[2].lower()
    value[3] = value[3].lower()
    # connect -to server1 hs

    #check if the first argument is ip or not

    if(not isIP(value[0])): #it's the name of a server
        #check if the server exists

        if(serverExists(data['servers'], value[0])):

            #check if the device exists

            if(deviceExists(data['servers'], value[1], value[0])):
                
                #ssh connection
                               
                #connect using details SERVER FOUND 
                
                value[0] = getServer(data['servers'], value[0])
               
                value[1] = getDevice(data['servers'][value[0]]['connected'], value[1])
                
                #adjusting the routing table 
                
                data['routeData'] = readRoutes()['routeData']
                adjustRouteTable(data, value)
                
                if(installing != 0):
                    latestConnection = []
                    toConnect = True
                    latestConnection.append(value[1])
                    latestConnection.append(data['users'])
                    latestConnection.append(data['port'])
                    latestConnection.append(value[0])
                    latestConnection.append(data['pswd'])
                   # sshConnect(value[1], data['users'], data['port'], value[0], data['pswd'])
                
                
                
            else:
                print(f"\033[1;31m DEVICENAME ({value[1]}) IS NOT CORRECT\n")
                sys.exit()

        else:
            
            #may be the user inserted the domain instead of ip
            
            gateway = getAddress(value[0])
            if(gateway != "none"):
                value[0] = gateway
                
                insert(data, value, installing)
            else:
            
                print(f"\033[1;31m SERVERNAME ({value[0]}) IS NOT CORRECT\n")
                sys.exit()
    
    else:
        
        data = insert(data, value, installing)
    return data

if(PYFILE in args): #means user wants to download

       
    if data_exists and file_exists:
        installed = True

    if(curr):
        installed = True
    

    #install the package if not installed

    if(not installed):

        pyModules = [ "jsons", "pytest-shutil" ,"subprocess.run"]

        
        
        print("\n ------------------  UPDATING --------------")
        res = subprocess.run(mainCommands["update"],shell=True ,check=True)
        
        
        print("\n ------------------  INSTALLING PYTHON3-PIP --------------")
        res = subprocess.run(mainCommands["pipInstall"],shell=True ,check=True)
      

        print("\n INSTALLING PYTHON MODULES...")
        pyModulesInstallation(pyModules)  #install all the dependencies


        #install dependencies 
        print("\n INSTALLING route COMMAND TOOLS...\n")
        subprocess.run(mainCommands["routeDownload"], shell=True, check=True)
        print("\n UPDATING")
        subprocess.run(mainCommands['update'], shell=True, check=True) 

       
        #create files to current path

        shutil.copyfile("./"+PYFILE, "./"+FILE_NAME) #creating copy in folder (connect.py to connect)

        #create json file 

        connectData = readRoutes()
        


        writeFile(DATA_FILE_NAME,connectData)
        os.mkdir(CONNECT_JSON)
        os.chmod(CONNECT_JSON, stat.S_IRWXO)
        
        writeFile(CONNECT_JSON+DATA_FILE_NAME,connectData)
        #give permission to json file
        os.chmod(CONNECT_JSON+DATA_FILE_NAME, stat.S_IRWXO)

        #write python path at  the start of the file

        pyPath = proccessWithResult(mainCommands['findPython']) #find python path

        #adding #! to path
        pyPath = "#!"+pyPath


        fileContent = readFile(FILE_NAME)
        
        pyPath += "\n"+fileContent #writing the path in first line

        writeFile(FILE_NAME, pyPath)


        #give permission to connect file

        print("\n INSTALLING CONNECT...\n")
        command = f"chmod +x {FILE_NAME}"
        subprocess.run(command, shell=True, check=True)


        #move all the files to the path
        command = f"sudo mv {FILE_NAME} {globalPath}"
        subprocess.run(command, shell=True, check=True)

        command = f"sudo mv {DATA_FILE_NAME} {globalPath}"
        subprocess.run(command, shell=True, check=True)

        print("\n INSTALLATION COMPLETED")
        
        connectData = connecter([DEFAULT_GATEWAY, "HS", DEFAULT_SUBNET,""],connectData, 0)
        writeFile(CONNECT_JSON+DATA_FILE_NAME,connectData)
        sys.exit()
        
        #create a defualt one for the first time
       
    # ------------------- INSTALLATION COMPLETE -----------

else:

     
    #routing begins with args

    #lowercase all the param keys

    for i in range(len(args)):
        if(args[i][0] == "-"):
            args[i] = args[i].lower()

    #open the file data before continue
    data = readFile(CONNECT_JSON+DATA_FILE_NAME)
    
    

    #loop through args
    x=0
    
    
    
    if("-devip" in args):
        y = args.index("-devip")
        value = combineArgs(y)
        
        if(len(value) == 1):
            
            if(isIP(value[0])):
                if("." in value[0]):
                    value[0] = value[0].split(".")[-1]
                
                data['lastPart'] = value[0]
                
            else:
                print(f"\033[1;31m argument should be an ip\n")
                sys.exit()
    elif("-p" in args):
        y = args.index("-p")
        value = combineArgs(y)
        
        if(len(value) == 1):
            if(value[0].isdigit()):
                data['port'] = int(value[0])
            else:
                print(f"\033[1;31m port is an integer\n")
                sys.exit()
            
    elif("-pswd" in args):
        y = args.index("-pswd")
        value = combineArgs(y)
        
        if(len(value) == 1):
            data['pswd'] = value[0]
    elif("-newname" in args):
        y = args.index("-newname")
        value = combineArgs(y)
        
        if(len(value) == 2):
            #old and new value
            
            if(serverExists(data['servers'], value[1])):
                print(f"\033[1;31m {value[1]} already exists!\n")
                sys.exit()
                
            elif(not serverExists(data['servers'], value[0])):
                print(f"\033[1;31m {value[1]} doesn't exists!\n")
                sys.exit()
            else:
                
                #changename
                
                data['servers'] = changeName(data['servers'], value[0], value[1])
        
            showCenters(data['servers'])
            
    elif("-send" in args):
        y = args.index("-send")
        value = combineArgs(y)
        
        if(len(value) == 3 and isSCP(value)):
            value2 = valueGenerator(value)
            data = connecter(value2, data, 1)
           
            toConnect = False
            value = sendFiles(value, data)
        
        elif(len(value) == 4 and isSCP(value)):
            if(folTrans(value)):
                value2 = valueGenerator(value)
                data = connecter(value2, data,1)
                
                toConnect = False
                sendFiles(value, data)
            else:
                print(f"\033[1;31m SYNTAX ERROR : to send a folder ad fol parameter\n -send <server> fol <localFolderLocation> <device>:<remoteLocation>\n")
                sys.exit()
        else:
            print(f"\033[1;31m The format should be : connect -send <servername> <localfile> <devicename ex.cpu>:<remotefile location>\n")
            sys.exit()
        
    for param in args:
        value = ""
        
        if(param == "-to"):
           
            #connect to a device or ip

            value = combineArgs(x)
            
            if("-devip" in args and len(value) > 0):
                
                name = value[0]
                
                ipe = getAddress(name)
                if(isIP(value[0])):
                    name = rebuild(DEFAULT_GATEWAY, value[0])
                elif(ipe != "none"):
                    name = ipe
                
                if(serverExists(data['servers'],name)):
                    
                    data['servers'] = replaceValues(data['servers'],name, data['lastPart'])
                    
            if(len(value) == 2):

                value.append(DEFAULT_SUBNET)
                value.append("")
                data = connecter(value, data,1)

            elif(len(value) == 3 and (not isSCP(value))):

                if(not isIP(value[2])):
                    value.append(value[2])
                    value[2] = DEFAULT_SUBNET
                
                value.append("")
                data = connecter(value, data,1)
            
            elif(len(value) == 3 and isSCP(value)):
                value2 = valueGenerator(value)
                data = connecter(value2, data,1)
                sendFiles(value, data)
                
            elif(len(value) == 4 and (not isSCP(value))):
                
                
                data = connecter(value, data,1)
                
            elif(len(value) == 4 and isSCP(value)):
                if(folTrans(value)):
                    value2 = valueGenerator(value)
                    data = connecter(value2, data,1)
                    sendFiles(value, data)
                
                else:
                    print(f"\033[1;31m SYNTAX ERROR : to send a folder ad fol parameter\n -send <server> fol <localFolderLocation> <device>:<remoteLocation>\n")
                    sys.exit()
                    
            showCenters(data['servers'])
                    
        elif(param == "-del"):
            
            value = combineArgs(x)
            
            if(len(value) == 1):
                
                if(not isIP(value[0])):
                    #check if it's a domain
                    ip = getAddress(value[0])
                    if(ip == "none"):
                        
                        #it's a server
                        if(serverExists(data['servers'], value[0])):
                            data['servers'] = deleteServer(data['servers'], value[0])
                        else:
                            print(f"\033[1;31m SERVERNAME ({value[0]}) IS NOT CORRECT\n")
                            sys.exit()
                    else:
                        
                        #it's a domain name
                        
                        value[0] = ip
                        data['servers'] = deleteServer(data['servers'], value[0])
                else:
                    #its an ip
                    
                    value[0] = rebuild(DEFAULT_GATEWAY, value[0])
                    data['servers'] = deleteServer(data['servers'], value[0])
            
            else:
                print(f"\033[1;31m provide only one argument for -del\n")
                sys.exit()

            showCenters(data['servers'])
        
                    
        elif(param == "-r"):
             showRouteTable()

        elif(param == "-help" or (param == "/usr/local/bin/connect" and len(args) ==1 ) ):
            showInstructions()
        
        elif(param == "-s"):
           showCenters(data['servers'])
        
        elif(param == "-uninstall"):
            
            uninstall()
           
        
        
        x+=1

       
   
    writeFile(CONNECT_JSON+DATA_FILE_NAME, data)
    if(toConnect):
        sshConnect(latestConnection[0], latestConnection[1], latestConnection[2], latestConnection[3], latestConnection[4])

            