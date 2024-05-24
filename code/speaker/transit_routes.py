import requests

def fetch_subway_status(line):
    url = "https://www.goodservice.io/api/routes?detailed=1"
    response = requests.get(url)
    # print(response.text)  # This will print the raw response to the console
    if response.status_code == 200:
        data = response.json()
        route_data = data["routes"].get(line, {})
        status = route_data.get("status", "Status unknown")
        return status
    else:
        return f"Failed to fetch subway status: {response.status_code}"
    
def train_status_phrase(train_line, status):
    return f'The {train_line}-Train Status is {status}'    

SUBWAY_LINES = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "6X",
    "7",
    "7X",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "FX",
    "G",
    "J",
    "L",
    "M",
    "N",
    "Q",
    "R",
    "GS",
    "FS",
    "H",
    "SI",
    "W",
    "Z",

]

if __name__ == "__main__":  # This block will only run when transit_routes.py is run directly, not when imported.
    for subway_line in SUBWAY_LINES:
        status = fetch_subway_status(subway_line)
        print(f"MTA {subway_line} Train Status: {status}")
