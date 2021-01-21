# Factory Default Tool for CSL Fixed RFID Readers

Command-line tool for putting CSL fixed readers back to factory default mode through the debug serial interface

### Related Products

[CS463 4-Port RFID Reader](https://www.convergence.com.hk/cs463/)

[CS203X Integrated RFID Reader](https://www.convergence.com.hk/cs203x/)

### Dependencies

- Python 3
- PySerial 
- ConfigParser


### Instructions

1. Power off the reader
2. Connect the debug serial port on the reader to your computer
3. Edit the config.ini file and enter your serial port information.  For Windows it would be COM{port number}.  For Mac it would be the device under /dev/tty.usbserial-{deviceId}
4. Run the Python script by:

	```
	> python3 CS463FactoryDefault.py
	```
5. Power up the reader and it will boot into recovery mode.  The entire file system will be refreshed to default


PyCharm IDE was used during development.