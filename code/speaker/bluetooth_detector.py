from bluepy.btle import Scanner, DefaultDelegate
import time

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


RSSI_THRESHOLD = -70  
AIRTAG_MAC = "aa:bb:cc:dd:ee:ff"  

def is_a_tag_nearby():
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0) 

    for dev in devices:
        if dev.addr.upper() == AIRTAG_MAC.upper() and dev.rssi > RSSI_THRESHOLD:
            print("AirTag detected with strong signal:", dev.addr, "RSSI:", dev.rssi)
            return True
        else:
            print("Device detected:", dev.addr, "RSSI:", dev.rssi)
    return False

while True:
    if is_a_tag_nearby():
        print("Your keys are nearby!")
    else:
        print("Your keys are not detected nearby.")
    
    time.sleep(60) 