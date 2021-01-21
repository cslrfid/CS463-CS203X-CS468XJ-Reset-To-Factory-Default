import sys
import serial
from datetime import datetime
from configparser import ConfigParser

serRead = ""
response = ""
timer = None
backupFileName = ""
config = ConfigParser()

try:
    config.read("config.ini")
    serPort = config.get("Serial", "Port")
    print("CSL Factory Default Tool")
    print("Serial Port: " + serPort)
    ser = serial.Serial(serPort, 115200, timeout=0.1)  # open serial port
except:
    print("Serial port cannot be opened")


def uboot_command(command, timeout):
    global response
    global serRead

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

    timer=datetime.now()
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


if ser.isOpen():
    ser.flush()
    print("(1) Power off your reader ")
    print("(2) Connect the serial cable from you computer to the debug serial port on the device.")
    print("(3) Power on the reader and wait...")
    response=""
    serRead=""

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

    response = ""
    ser.write(b"boot\n")
    if not read_serial_until_string_pattern("imx6dlsabresd login: ", 10):
        # timed out
        ser.close()
        print(">> Error entering recovery partition mode.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"root\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~# ", 5):
        # timed out
        ser.close()
        print(">> Error logging into partition mode.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"mkdir -p backuprootfs\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~# ", 5):
        # timed out
        ser.close()
        print(">> Error creating /home/root/backuprootfs.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"mount /dev/mmcblk2p6 ~/backuprootfs/\n")
    if not (read_serial_until_string_pattern("root@imx6dlsabresd:~# ", 5) and
            ("mounted filesystem" in response)):
        # timed out
        ser.close()
        print(">> Unable to mount /dev/mmcblk2p6.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"ls ~/backuprootfs/ | grep FactoryDefault.tar.gz\n")
    if not read_serial_until_string_pattern("FactoryDefault.tar.gz\r\nroot@imx6dlsabresd:~# ", 5):
        # timed out
        ser.close()
        print(">> Unable to found recovery image file.  Program abort")
        sys.exit()

    # save the file name
    startIndex=0
    endIndex=0
    startIndex=response.find("rootfs",
                             len("ls ~/backuprootfs/ | grep FactoryDefault.tar.gz\n"))
    endIndex=response.find("root@imx6dlsabresd:~#") - 2
    backupFileName = response[startIndex:endIndex]


    response = ""
    ser.write(b"mkdir -p originalrootfs\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~# ", 5):
        # timed out
        ser.close()
        print(">> Error creating /home/root/originalrootfs.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"mount /dev/mmcblk2p2 ~/originalrootfs/\n")
    if not (read_serial_until_string_pattern("root@imx6dlsabresd:~# ", 5) and
            ("mounted filesystem" in response)):
        # timed out
        ser.close()
        print(">> Unable to mount /dev/mmcblk2p2.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"ls ~/originalrootfs/ | grep opt\n")
    if not read_serial_until_string_pattern("opt\r\nroot@imx6dlsabresd:~#", 5):
        # timed out
        ser.close()
        print(">> Unable to find original rootfs in mounted folder.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"cd ~/originalrootfs\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~/originalrootfs# ", 5):
        # timed out
        ser.close()
        print(">> Unable to enter original rootfs.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"rm * -rf\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~/originalrootfs# ", 300):
        # timed out
        ser.close()
        print(">> Unable to delete original rootfs.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"export EXTRACT_UNSAFE_SYMLINKS=1\n")
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~/originalrootfs# ", 300):
        # timed out
        ser.close()
        print(">> Unable to configure extraction process.  Program abort")
        sys.exit()

    response = ""
    ser.write(("tar xvzf ~/backuprootfs/" + backupFileName + "\n").encode('utf-8'))
    if not read_serial_until_string_pattern("root@imx6dlsabresd:~/originalrootfs# ", 1200):
        # timed out
        ser.close()
        print(">> Unable to restore rootfs.  Program abort")
        sys.exit()

    response = ""
    ser.write(b"ls /etc/systemd/system | grep default.target\n")
    if not read_serial_until_string_pattern("default.target\r\nroot@imx6dlsabresd:~/originalrootfs# ", 5):
        # timed out
        ser.close()
        print(">> Unable to find original rootfs in mounted folder.  Program abort")
        sys.exit()

    print("\n>> Factory default completed.  Please power cycle the reader")

else:
    print("Serial port cannot be opened")


