import sys
import time
import serial
import requests
from datetime import datetime
from configparser import ConfigParser

serRead = ""
response = ""
timer = None
backupFileName = ""
hostname = ""
sessionId = ""
config = ConfigParser()
regDnfRepository = ""

try:
    config.read("config.ini")
    serPort = config.get("Serial", "Port")
    defaultIP = config.get("Network", "DefaultIP")
    defaultGateway = config.get("Network", "DefaultGateway")
    defaultMask = config.get("Network", "DefaultMask")
    regDnfRepository = config.get("Configurations", "DnfRepoUrl")
    print("CSL Factory Default Tool")
    print("Serial Port: " + serPort)
    ser = serial.Serial(serPort, 115200, timeout=0.1)  # open serial port
except:
    print("Serial port cannot be opened")


def uboot_command(command, timeout):
    global response
    global serRead
    global timer

    ser.write(command + b"\n")
    timer = datetime.now()
    while True:
        serRead = ser.read().decode("UTF-8", "replace")
        print(serRead, end="")
        response += serRead
        rtn = command.decode("UTF-8", "replace") + "\r\n=>"
        if rtn in response:
            # send space character to stop reader at bootloader mode
            return True
        if (datetime.now() - timer).seconds > timeout:
            return False


def read_serial_until_string_pattern(StringPattern, timeout):
    global serRead
    global response
    global timer

    timer = datetime.now()
    while True:
        try:
            serRead = ser.read().decode("UTF-8", "replace")
            print(serRead, end="")
            response += serRead
            if len(response) > 2000:
                response = response[len(response)-2000:]

            if StringPattern in response:
                return True;

            if (datetime.now() - timer).seconds > timeout:
                #timed out
                return False
        except:
            print(">> Error reading serial port.  Program abort")
            ser.close()
            sys.exit()


def send_serial_command(command, resp, timeout):
    global response
    response = ""
    ser.write(command)
    if not read_serial_until_string_pattern(resp, timeout):
        # timed out
        ser.close()
        print(">> Error sending serial commands '{}'.  Program abort".format(command))
        sys.exit()


def http_command_login(ipaddr):
    global sessionId

    p = (("command", "login"), ("username", "root"), ("password", "csl"))
    r = requests.get("http://" + ipaddr + "/API", params=p, timeout=10.0)
    if r.status_code == 200:
        content = r.content.decode("UTF-8")
        if content.find("session_id=") >= 0:
            sessionId = content[content.find("session_id=") + 11:content.find("session_id=") + 11 + 8]
            return True
    return False


def http_command_forcelogout(ipaddr):
    p = (("command", "forceLogout"), ("username", "root"), ("password", "csl"))
    r = requests.get("http://" + ipaddr + "/API", params=p, timeout=10.0)
    if r.status_code == 200:
        if r.content.decode("UTF-8").find("OK") >= 0:
            return True
    return False


def http_command_setNetworkConfig(ipaddr, mask, defaultGw):
    global sessionId

    p = (("session_id", sessionId),
         ("command", "setNetworkConfig"),
         ("type", "ethernet"),
         ("dhcpmode", "0"),
         ("ip", ipaddr),
         ("mask", mask),
         ("gateway", defaultGw),
         ("dns_server1", "8.8.8.8"),
         ("dns_server2", defaultGw))

    r = requests.get("http://" + ipaddr + "/API", params=p, timeout=10.0)
    if r.status_code == 200:
        if r.content.decode("UTF-8").find("OK:") >= 0:
            return True
    return False

if ser.isOpen():
    ser.flush()
    print("(1) Power off your reader ")
    print("(2) Connect the serial cable from you computer to the debug serial port on the device.")
    print("(3) Power on the reader and wait...")
    response = ""
    serRead = ""

    if read_serial_until_string_pattern("Hit any key to stop autoboot:", 300):
        # send space character to stop reader at bootloader mode
        response=""
        ser.write(b" ")
    else:
        # timed out
        ser.close()
        print(">> Error entering bootloader mode.  Program abort")
        sys.exit()

    if not read_serial_until_string_pattern("=> ", 5):
        # timed out
        ser.close()
        print(">> Error entering bootloader mode.  Program abort")
        sys.exit()

    response = ""
    # set mmc root to recovery partition
    if not uboot_command(b"setenv mmcroot /dev/mmcblk2p8 rootwait rw", 5):
        # timed out
        ser.close()
        print(">> Response timed out.  Program abort")
        sys.exit()

    send_serial_command(b"boot\n", "imx6dlsabresd login: ", 10)
    send_serial_command(b"root\n", "root@imx6dlsabresd:~# ", 5)
    send_serial_command(b"mkdir -p backuprootfs\n", "root@imx6dlsabresd:~# ", 5)
    send_serial_command(b"mount /dev/mmcblk2p6 ~/backuprootfs/\n", "root@imx6dlsabresd:~# ", 5)
    if not "mounted filesystem" in response:
        ser.close()
        print(">> Unable to mount /dev/mmcblk2p6.  Program abort")
        sys.exit()
    send_serial_command(b"ls ~/backuprootfs/ | grep -E 'FactoryDefault.tar.gz|factorydefault.tar.gz'\n", ".tar.gz\r\nroot@imx6dlsabresd:~# ", 5)

    # save the file name
    startIndex = 0
    endIndex = 0
    startIndex = response.find("rootfs",
                             len("ls ~/backuprootfs/ | grep -E 'FactoryDefault.tar.gz|factorydefault.tar.gz'\n"))
    endIndex = response.find("root@imx6dlsabresd:~#") - 2
    backupFileName = response[startIndex:endIndex]

    send_serial_command(b"mkdir -p originalrootfs\n", "root@imx6dlsabresd:~# ", 5)
    send_serial_command(b"mount /dev/mmcblk2p2 ~/originalrootfs/\n", "root@imx6dlsabresd:~# ", 5)
    if not "mounted filesystem" in response:
        ser.close()
        print(">> Unable to mount /dev/mmcblk2p2.  Program abort")
        sys.exit()
    send_serial_command(b"ls ~/originalrootfs/ | grep opt\n", "opt\r\nroot@imx6dlsabresd:~#", 5)
    send_serial_command(b"cd ~/originalrootfs\n", "root@imx6dlsabresd:~/originalrootfs# ", 5)
    send_serial_command(b"rm * -rf\n", "root@imx6dlsabresd:~/originalrootfs# ", 300)
    send_serial_command(b"export EXTRACT_UNSAFE_SYMLINKS=1\n", "root@imx6dlsabresd:~/originalrootfs# ", 5)
    send_serial_command(("tar xvzf ~/backuprootfs/" + backupFileName + "\n").encode('utf-8'), "root@imx6dlsabresd:~/originalrootfs# ", 1200)
    send_serial_command(b"ls /etc/systemd/system | grep default.target\n", "default.target\r\nroot@imx6dlsabresd:~/originalrootfs# ", 5)
    send_serial_command(b"reboot\n", "login: ", 60)
    send_serial_command(b"root\n", "Password: ", 5)
    send_serial_command(b"csl\n", ":~# ", 5)
    send_serial_command(b"/opt/hostnameUnique_set\n", "~# ", 5)

    # extract hostname
    startIndex = response.find("/opt/hostnameUnique_set") + len("/opt/hostnameUnique_set") + 2
    endIndex = response.find("root@") - 2
    if startIndex < 0 or endIndex < 0 or (startIndex > endIndex):
        # timed out
        ser.close()
        print(">> Error setting hostname  Program abort")
        sys.exit()
    hostname = response[startIndex:endIndex]

    # hostname = "csl-7b8401f6"
    send_serial_command(b"reboot\n", hostname + " login: ", 60)

    if defaultIP == "":
        print("\n>> Factory default completed.  Program exit.")
        sys.exit()

    # Wait for two minutes until t
    for i in range(120, -1, -1):
        time.sleep(1)
        print("\r>> Wait for {0:d} seconds".format(i), end="")

    send_serial_command(b"root\n", "Password: ", 5)
    send_serial_command(b"csl\n", "root@" + hostname + ":~# ", 5)

    print(">> Set new IP address")
    send_serial_command(b"ps aux | grep connman\n", "root@" + hostname + ":~# ", 5)

    psOutput = response.split("\r\n");
    ps = ""
    for line in psOutput:
        if line.find("/usr/sbin/connmand -n") >= 0:
            ps = line.split()[1]

    if ps == "":
        # timed out
        ser.close()
        print(">> Unable to reboot device.  Program abort")
        sys.exit()

    send_serial_command(("kill " + ps + "\n").encode("utf-8"), "root@" + hostname + ":~# ", 5)
    send_serial_command(b"ifconfig eth0 up\n", "root@" + hostname + ":~# ", 5)
    send_serial_command(("ifconfig eth0 " + defaultIP + "\n").encode("utf-8"), "root@" + hostname + ":~# ", 5)

    # Wait for two minutes until t
    for i in range(150, -1, -1):
        time.sleep(1)
        print("\r>> Wait for {0:d} seconds".format(i), end="")

    print(">> Web interface is now accessible through new IP.  Complete network configurations through HTTP commands")

    # login
    if not http_command_login(defaultIP):
        ser.close()
        print(">> Unable to login reader through HTTP.  Program abort")
        sys.exit()

    # set network config
    if not http_command_setNetworkConfig(defaultIP, defaultMask, defaultGateway):
        ser.close()
        print(">> Unable to set network config through HTTP.  Program abort")
        sys.exit()

    if regDnfRepository != "":
        print(">> Register DNF repository for additional packages")
        repoFileCmd = "printf \"[cslrepo]\nname=CSL Intelligent Reader Repository\nbaseurl={" \
                      "}\nenabled=1\ngpgcheck=0\" > /etc/yum.repos.d/csl-remote-repo.repo\n".format(regDnfRepository)
        send_serial_command(repoFileCmd.encode("utf-8"), ":~# ", 5)

    send_serial_command(b"reboot\n", hostname + " login: ", 60)

    print("\n>> Factory default completed.  Program exit.")

else:
    print("Serial port cannot be opened")


