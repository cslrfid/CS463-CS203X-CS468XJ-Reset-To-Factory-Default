# Factory Default Tool for CSL Fixed RFID Readers

Command-line tool for putting CSL fixed readers back to factory default mode through the debug serial interface

### Related Products

[CS463 4-Port RFID Reader](https://www.convergence.com.hk/cs463/)

[CS203X Integrated RFID Reader](https://www.convergence.com.hk/cs203x/)

### Instructions

1. Power off the reader
2. Connect the debug serial port on the reader to your computer
3. Download the package and extract the zip file under the *dist* folder
3. Edit the *config.ini* file and enter your serial port information.  For Windows it would be COM{port number}.  For Mac it would be the device under /dev/tty.usbserial-{deviceId}
	
	```
	[Serial]
	Port = COM6
	```
	
4. The program can also set the IP address of the reader after resetting the system.  For doing that, you will need to update the IP information in *config.ini*:
	
	```
	[Network]
	DefaultIP = 192.168.1.100
	DefaultMask = 255.255.255.0
	DefaultGateway = 192.168.1.1
	```
	After that, please also connect your computer to the reader via the same network being configure.  For the example above, the IP address of the network interface connected to the reader should be in the same network 192.168.1.XXX 
	
	If network information is not entered in *config.ini*, IP address will not be set after factory default and it will be stay in the default value 192.168.25.160.
	
5. Run the file CS463FactoryDefault.exe in the folder
6. Power up the reader and it will boot into recovery mode.  The entire file system will be refreshed to default.  The process would usually take around 15 minutes

