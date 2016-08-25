# Deploying (IRF-)(iMC-)config and software on HP5130 24/48 Ports (PoE) Switches
#
#------------------------------------------------------------------------------------
# Author:      Remi Batist / AXEZ ICT Solutions
# Version:     3.1
#
# Created:     16-08-2016
# Comments:    remi.batist@axez.nl
#
# Use at own risk, with this and any script recommend testing in non-production first
#------------------------------------------------------------------------------------
#	How to use de script;
#	1) On the HP IMC server(or other tftp-srver), put this script and software in the "%IMC Install Folder%\server\tmp" folder.
#	2) Set the DHCP-Server in the "deploy" network with this script as bootfile. Example on a Comware devices below.
#			dhcp enable
#			dhcp server forbid 10.0.1.1 10.0.1.200
#			dhcp server ip-pool v1
# 			gateway 10.0.1.1
# 			bootfile-name 5130_irf-config.py
# 			tftp-server ip 10.0.1.100
# 			network 10.0.1.0 24
#	3) Boot a switch without a config-file and connect it to the "deploy" network.
#
# You can change the custom settings below when needed  ####

# TFTP/IMC-Server Settings
tftpsrv = "10.0.1.100"
tftpfolder = "" # must end with //
imc_bootfile = "autocfg_startup.cfg" # This file always uses TFTP
imc_snmpread = 'iMCread'
imc_snmpwrite = 'iMCwrite'
# FTP-Server Settings
ftpsrv = "192.168.0.20"
ftpfolder = "anonymous//" # must end with //
ftpusr = ""
ftppsw = "none"
use_ftp_for_files = False # True or False for files below
# 5130 Firmware + Optional Files
bootfile = "5130ei-cmw710-boot-r3111p07.bin"
sysfile = "5130ei-cmw710-system-r3111p07.bin"
poefile = "S5130EI-POE-145.bin"
optional_files = ["ap_config.py", "int_import.py"]
# Irf Settings
irfports_24ports = {1:["/0/25",""],2:["/0/27",""]}
irfports_48ports = {1:["/0/49",""],2:["/0/51",""]}
irf_prio_numbers = {"1":"32","2":"31","3":"30","4":"29","5":"28","6":"27","7":"26","8":"25","9":"24"}

#### Importing python modules
import comware
import os
import sys
import time
import termios

#### RAW user-input module
fd = sys.stdin.fileno();
new = termios.tcgetattr(fd)
new[3] = new[3] | termios.ICANON | termios.ECHO
new[6] [termios.VMIN] = 1
new[6] [termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, new)
termios.tcsendbreak(fd,0)

#### Notification for Starting
print (('\n' * 5) + "Starting script for deploying IRF-config and software on 5130 switches\n"
        "\nPlease wait while getting the current versions and settings...."
        )

#### Getting Current settings and versions
def SwitchInput():
    sys.stdout.write("\r%d%%" % 0)
    sys.stdout.flush()
    #### Enable local logging: flash:/logfile/logfile.log
    comware.CLI('system ; info-center logfile frequency 1 ; info-center source SHELL logfile level debugging ; info-center source CFGMAN logfile level debugging', False)
    #### Get Current IRF Member
    memberid = (comware.CLI('display irf link', False).get_output())[1][7]
    sys.stdout.write("\r%d%%" % 20)
    sys.stdout.flush()
    #### Get SwitchModel
    model = "48 Ports" if "/0/48" in str(comware.CLI('display int brief', False).get_output()) else "24 Ports"
    sys.stdout.write("\r%d%%" % 40)
    sys.stdout.flush()
    #### Get Mac-address
    mac_address = comware.CLI('dis device manuinfo | in MAC_ADDRESS', False).get_output()[1][23:37]
    sys.stdout.write("\r%d%%" % 60)
    sys.stdout.flush()
    #### Get Switch Software Version
    sw_version = comware.CLI('display version | in Software', False).get_output()[1]
    sys.stdout.write("\r%d%%" % 80)
    sys.stdout.flush()
    #### Get PoE Software Version
    try:
        comware.CLI('system ; int gig' + memberid + '/0/1 ; poe enable ', False)
        poe_version = comware.CLI('display poe pse | in Software', False).get_output()[1][36:40]
    except SystemError:
        poe_version = 'N/A'
    sys.stdout.write("\r%d%%\n" % 100)
    sys.stdout.flush()
    return memberid, model, mac_address, sw_version, poe_version


#### Startmenu for deploying the switch
def StartMenu(memberid, model, mac_address, sw_version, poe_version):
    checkbox1 = checkbox2 = checkbox3 = checkbox4 = checkbox5 = set_memberid = ''
    Menu = True
    while Menu:
        print   "\n" * 5 + "Current switch information:",\
                "\n  Current switch model         " + str(model),\
                "\n  Current MAC-address          " + str(mac_address),\
                "\n  Current software version     " + str(sw_version),\
                "\n  Current PoE version          " + str(poe_version),\
                "\n  Current Member-ID            " + str(memberid),\
                "\n  Newly chosen Member-ID       " + str(set_memberid),\
                "\n" * 2 + "Files ready for installation:",\
                "\n  Switch Boot-file             " + str(bootfile),\
                "\n  Switch System-file           " + str(sysfile),\
                "\n  Switch PoE software-file     " + str(poefile),\
                "\n" * 2 + "%-60s %-1s %-1s %-1s" % ("1.Update switch firmware", "[", checkbox1, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("2.Update PoE firmware", "[", checkbox2, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("3.Download optional files", "[", checkbox3, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("4.Change IRF Member-ID (and set IRF-port-config)", "[", checkbox4, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("5.Trigger iMC for deployment (min. firmware v3109P05!)", "[", checkbox5, "]"),\
                "\n%-60s " % ("6.Run selection"),\
                "\n%-60s " % ("7.Exit/Quit and start CLI"),\
                "\n%-60s " % ("8.Exit/Quit and reboot")
        ans=raw_input("\nWhat would you like to do? ")
        if ans=="1":
            checkbox1 = "X"
            checkbox6 = ""
        elif ans=="2":
            if not poe_version=="N/A":
                checkbox2 = "X"
            else:
                checkbox2 = ""
        elif ans=="3":
            checkbox3 = "X"
        elif ans=="4":
            set_memberid = raw_input("Enter new Member-ID: ")
            checkbox4 = "X"
        elif ans=="5":
            checkbox5 = "X"
        elif ans=="6":
            Menu = False
        elif ans=="7":
            print "\nQuiting script, starting CLI...\n"
            quit()
        elif ans=="8":
            print "\nQuiting script and rebooting...\n"
            comware.CLI('reboot force')
            quit()
        else:
            print("\n Not Valid Choice Try again")
    return checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, set_memberid

#### Switch software update
def SoftwareUpdate(checkbox1):
    if checkbox1 == "X":
        print "\nDownloading Switch Firmware....\n"
        try:
            if use_ftp_for_files:
                comware.CLI("copy ftp://" + ftpusr + ":" + ftppsw + "@" + ftpsrv + "//" + ftpfolder + bootfile + " " + bootfile)
                comware.CLI("copy ftp://" + ftpusr + ":" + ftppsw + "@" + ftpsrv + "//" + ftpfolder + sysfile + " " + sysfile)
            else:
                comware.CLI("copy tftp://" + tftpsrv + "//" + tftpfolder + bootfile + " " + bootfile)
                comware.CLI("copy tftp://" + tftpsrv + "//" + tftpfolder + sysfile + " " + sysfile)
            comware.CLI("boot-loader file boot flash:/" + bootfile + " system flash:/" + sysfile + " all main")
        except SystemError:
            print "\nFirmware upgrade unsuccessful, check server or files\n"
        else:
            print "\nFirmware upgrade successful\n"
    else:
        print "\nSkipping Switch Firmware update"

#### Switch poe update
def PoEUpdate(checkbox2, memberid):
    if checkbox2 == 'X':
        # PoE PSE Numbers
        poe_pse_numbers = {"1":"4","2":"7","3":"10","4":"13","5":"16","6":"19","7":"22","8":"25","9":"26"}
        print "\nUpdating PoE Firmware....\n"
        try:
            if use_ftp_for_files:
                comware.CLI("copy ftp://" + ftpusr + ":" + ftppsw + "@" + ftpsrv + "//" + ftpfolder + poefile + " " + poefile)
            else:
                comware.CLI("copy tftp://" + tftpsrv + "//" + tftpfolder + poefile + " " + poefile)
            comware.CLI("system ; poe update full " + poefile + " pse " + str(poe_pse_numbers[memberid]))
        except SystemError:
            print "\nPoE Firmware upgrade unsuccessful, check server or file\n"
        else:
            print "\nPoE Firmware upgrade successful\n"
    else:
        print "\nSkipping PoE firmware update"


#### Download optional files

def OptFiles(checkbox3):
    if checkbox3 == 'X':
        print "\nDownloading optional file(s)..."
        try:
            for file in optional_files:
                if use_ftp_for_files:
                    comware.CLI("copy ftp://" + ftpusr + ":" + ftppsw + "@" + ftpsrv + "//" + ftpfolder + file + " " + file)
                else:
                    comware.CLI("copy tftp://" + tftpsrv + "//" + tftpfolder + file + " " + file)
        except SystemError:
            print "\nDownload optional file(s) unsuccessful, check server or files\n"
        else:
            print "\nDownload optional file(s) successful\n"
    else:
        print "\nSkipping optional file(s)"

#### Change IRF MemberID
def ChangeIRFMemberID(memberid, checkbox4, set_memberid):
    if checkbox4 == 'X':
        print "\nChanging IRF MemberID..."
        comware.CLI("system ; irf member " + memberid + " renumber " + set_memberid)
    else:
        print "\nskipping IRF MemberID Change"


#### Set IRFPorts in startup config
def SetIRFPorts(memberid, model, checkbox4, checkbox5, set_memberid):
    if checkbox4 == 'X' and checkbox5 == "":
        if model == "48 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 48 ports switch...\n'
        if model == "24 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 24 ports switch...\n'
        set_prio = irf_prio_numbers[set_memberid]
        startup_file = open('flash:/startup.cfg', 'w')
        startup_file.write("\nirf member "+ set_memberid +" priority "+ set_prio + "\n")
        startup_file.write("\nirf-port "+ set_memberid +"/1")
        for port in (port for port in irfports_24ports[1] if port and model == "24 Ports"):
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + port + '\n')
        for port in (port for port in irfports_48ports[1] if port and model == "48 Ports"):
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + port + '\n')
        startup_file.write("\nirf-port "+ set_memberid +"/2")
        for port in (port for port in irfports_24ports[2] if port and model == "24 Ports"):
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + port + '\n')
        for port in (port for port in irfports_48ports[2] if port and model == "48 Ports"):
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + port + '\n')
        startup_file.close()
        comware.CLI("startup saved-configuration startup.cfg")
    else:
        print "\nSkipping IRF-Port-config"

#### Trigger iMC for auto-deployment
def TriggeriMC(checkbox5):
    if checkbox5 == 'X':
        print "\nTriggering iMC for deploy, please wait..."
        comware.CLI('system ; snmp-agent ; snmp-agent community read ' + imc_snmpread + ' ; snmp-agent community write ' + imc_snmpwrite + ' ; snmp-agent sys-info version all')
        try:
            comware.CLI('tftp ' + tftpsrv + ' get ' + imc_bootfile + ' tmp.cfg')
        except SystemError:
            print "\nDownload boot-file unsuccessful, check tftpsrv or imc_bootfile file\n"
        else:
            print "\nDownload boot-file successful\n"
            debug = ""
            for s in range(300):
                    sys.stdout.write("\r%s%s%s" % ("iMC Triggered successfully, waiting for config...", str(300 - s), " seconds remaining"))
                    sys.stdout.flush()
                    time.sleep( 1 )
    else:
        print "\nSkipping iMC deploy"

def Reboot():
    print('reboot force')
    comware.CLI('reboot force')
    quit()


#### Define main function
def main():
    try:
        (memberid, model, mac_address, sw_version, poe_version) = SwitchInput()
        (checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, set_memberid) = StartMenu(memberid, model, mac_address, sw_version, poe_version)
        SoftwareUpdate(checkbox1)
        PoEUpdate(checkbox2, memberid)
        OptFiles(checkbox3)
        ChangeIRFMemberID(memberid, checkbox4, set_memberid)
        SetIRFPorts(memberid, model, checkbox4, checkbox5, set_memberid)
        TriggeriMC(checkbox5)
        Reboot()
    except (EOFError, KeyboardInterrupt):
        print "\n\nquiting script!!!...."
        quit()

if __name__ == "__main__":
    main()


