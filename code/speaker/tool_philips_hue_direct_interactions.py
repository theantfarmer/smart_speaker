import hashlib
import re
import os
import time
import json
import requests
import time
import ssl
import requests
import warnings
from zeroconf import ServiceBrowser, Zeroconf

# this module was setup for the purpose of setting and maintaining
# philips hue wake up automations, but they are not currently 
# avlailable via the api


# Suppress only the single warning from urllib3 needed.
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

paired_philips_hue_bridges = {}

class HueBridgeListener:
    def __init__(self):
        self.bridges = []

    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            self.bridges.append(info.parsed_addresses()[0])
            
    def update_service(self, zeroconf, type, name):
        pass 

def find_and_pair_new_bridges():
    global paired_philips_hue_bridges
    while True:
        unpaired_bridges = []
        try:
            zeroconf = Zeroconf()
            listener = HueBridgeListener()
            browser = ServiceBrowser(zeroconf, "_hue._tcp.local.", listener)
            
            time.sleep(5)  # Wait for discovery
            unpaired_bridges = [bridge for bridge in listener.bridges if bridge not in paired_philips_hue_bridges.keys()]
            zeroconf.close()
            if unpaired_bridges:
                print("Unpaired bridges found:")
                for bridge in unpaired_bridges:
                    print(bridge)
                print("Please press the link button on the bridge(s).")
                start_time = time.time()
                while time.time() - start_time < 600 and len(unpaired_bridges) > 0:  # 10 minutes
                    for ip in unpaired_bridges:
                        try:
                            # Retrieve the certificate
                            cert = ssl.get_server_certificate((ip, 443))
                            cert_fingerprint = hashlib.sha256(cert.encode()).hexdigest()
                            # Attempt to pair with the bridge
                            response = requests.post(f"https://{ip}/api", 
                                                    json={"devicetype": "my_hue_app", "generateclientkey": True}, 
                                                    verify=False)  # We use verify=False here because we're handling the cert manually
                            if response.status_code == 200:
                                result = response.json()[0]
                                if 'success' in result:
                                    # Extract information from the pairing response
                                    username = result['success']['username']
                                    clientkey = result['success'].get('clientkey')  # This might be None if not generated
                                    print(f"Successfully paired with bridge at {ip}")
                                    # Get additional bridge information
                                    bridge_info_response = requests.get(f"https://{ip}/api/{username}/config", verify=False)
                                    if bridge_info_response.status_code == 200:
                                        bridge_info = bridge_info_response.json()
                                        bridge_id = bridge_info.get('bridgeid', 'Unknown')
                                        bridge_name = bridge_info.get('name', 'Unknown')
                                        # Generate a filename for the certificate
                                        if not os.path.exists('certs'):
                                            os.makedirs('certs')
                                        cert_filename = f"bridge_{bridge_id}.pem"
                                        cert_path = os.path.join('certs', cert_filename)
                                        # Save the certificate to a file
                                        with open(cert_path, 'w') as cert_file:
                                            cert_file.write(cert)
                                            
                                    # Update the dictionary with the new bridge, including the certificate and clientkey
                                    newly_paired_bridge = {
                                        "name": bridge_name,
                                        "username": username,
                                        "bridge_id": bridge_id,
                                        "clientkey": clientkey,
                                        "cert_file": cert_path,
                                        "cert_fingerprint": cert_fingerprint
                                    }

                                    # Then, we add this to paired_philips_hue_bridges
                                    paired_philips_hue_bridges[ip] = newly_paired_bridge
                                    
                                    # Update dont_tell.py immediately after each successful pairing
                                    with open('dont_tell.py', 'r+') as file:
                                        content = file.read()
                                        pattern = r'paired_philips_hue_bridges\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}'
                                        
                                        if re.search(pattern, content, re.DOTALL):
                                            # Replace the entire paired_philips_hue_bridges dictionary
                                            new_content = re.sub(pattern, 
                                                                f"paired_philips_hue_bridges = {repr(paired_philips_hue_bridges)}", 
                                                                content, 
                                                                flags=re.DOTALL)
                                            file.seek(0)
                                            file.write(new_content)
                                        else:
                                            # If the dictionary doesn't exist, append it to the end
                                            file.seek(0, 2)  # Go to the end of the file
                                            file.write(f"\npaired_philips_hue_bridges = {repr(paired_philips_hue_bridges)}\n")

                                    print(f"Pairing information for {ip} has been updated in dont_tell.py")
                                    unpaired_bridges.remove(ip)
                                    load_paired_bridges()
                        except requests.RequestException:
                            print(f"Error connecting to bridge at {ip}")
                        time.sleep(2)
                if unpaired_bridges:
                    print("Some bridges remain unpaired. They will be tried again in the next cycle.")
            else:
                load_paired_bridges()
        except Exception as e:
            print(f"Error in bridge discovery or pairing: {e}")
        time.sleep(5)
        
def schedule_handler():
    all_schedules = {}
    verified_bridges = load_paired_bridges(debug=False)

    for ip, bridge_info in verified_bridges.items():
        try:
            username = bridge_info['username']
            bridge_name = bridge_info['name']
            url = f"https://{ip}/api/{username}/schedules"
            
            response = requests.get(url, verify=False)  # Using verify=False as we're handling cert verification manually
            
            if response.status_code == 200:
                schedules = response.json()
                all_schedules[bridge_name] = schedules
                print(f"\nSchedules for bridge: {bridge_name}")
                print("=" * 50)
                
                if not schedules:
                    print("No schedules found for this bridge.")
                else:
                    for schedule_id, schedule_info in schedules.items():
                        print(f"\nSchedule ID: {schedule_id}")
                        print("-" * 30)
                        for key, value in schedule_info.items():
                            if key == "command":
                                print("Command:")
                                print(json.dumps(value, indent=2))
                            else:
                                print(f"{key.capitalize()}: {value}")
                        print("-" * 30)
            else:
                print(f"Failed to retrieve schedules from bridge: {bridge_name}. Status code: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to bridge at {ip}: {e}")
        except KeyError as e:
            print(f"Missing key in bridge_info for {ip}: {e}")
        except Exception as e:
            print(f"Unexpected error processing bridge at {ip}: {e}")
    
    return all_schedules


def load_paired_bridges(debug=True):
    global paired_philips_hue_bridges
    verified_bridges = {}

    try:
        from dont_tell import paired_philips_hue_bridges
    except ImportError:
        find_and_pair_new_bridges()
    
    while True:
        for ip, bridge_info in paired_philips_hue_bridges.items():
            try:
                username = bridge_info['username']
                bridge_id = bridge_info['bridge_id']
                name = bridge_info['name']
                cert_path = bridge_info['cert_file']
                saved_fingerprint = bridge_info['cert_fingerprint']
                
                current_cert = ssl.get_server_certificate((ip, 443))
                current_fingerprint = hashlib.sha256(current_cert.encode()).hexdigest()


                if debug:
                    print(f"Attempting to connect to bridge: {name} (ID: {bridge_id})")
                    print(f"IP Address: {ip}")
                    print(f"Username: {username}")
                    print(f"Certificate file: {cert_path}")
                    print(f"Certificate file exists: {os.path.exists(cert_path)}")

                if os.path.exists(cert_path):
                    if current_fingerprint == saved_fingerprint:
                        # Certificate matches what we saved, proceed with connection
                        response = requests.get(f"https://{ip}/api/{username}/config", 
                                                verify=False)  
                        if response.status_code == 200:
                            print(f"Successfully verified bridge at {ip}")
                            verified_bridges[ip] = bridge_info
                        else:
                            print(f"Bridge ID mismatch for {ip}. Stored: {bridge_id}, Received: {config['bridgeid']}")
                else:
                    print(f"Failed to connect to bridge at {ip}. Status code: {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to bridge at {ip}: {e}")
            except KeyError as e:
                print(f"Missing key in bridge_info for {ip}: {e}")
            except Exception as e:
                print(f"Unexpected error processing bridge at {ip}: {e}")

        return verified_bridges

if __name__ == "__main__":
    schedules = schedule_handler()