HA_URL = "http://192.168.0.86:8123" 
ENTITY_ID = "media_player.living_room_display"
STATUS_URL= "https://emasjidlive.co.uk/listen/leytonstonemasjid"
# The source where you get the URL (e.g., a website or log file)
# Replace this with the logic that fetches the raw text/URL
raw_source_url = "https://relay.emasjidlive.uk/leytonstonemasjid"

# Global variable to track the last used token
last_token = None

def extract_and_cast(rawSource):
    global last_token
    regex_pattern = r"token=(?P<token>[^&]+)&expires=(?P<expires>\d+)"
    match = re.search(regex_pattern,rawSource )
    
    if match:
        current_token = match.group('token')
        current_expires= match.group('expires')
        if current_token != last_token:
            print(f"New token detected: {current_token}. Updating stream...")
            print(f"New expiry {current_expires}. ")
            # 3. Prepare the Home Assistant API Call
            headers = {
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "entity_id": ENTITY_ID,
                "media_content_id": raw_source_url+f"?token={current_token}&expires={current_expires}", # The full URL
                "media_content_type": "url"
            }
            
            endpoint = f"{HA_URL}/api/services/media_player/play_media"
            
            try:
                response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
                if response.status_code == 200:
                    print("Successfully updated Home Assistant.")
                    last_token = current_token # Update our tracker
                else:
                    print(f"HA Error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Connection failed: {e}")
        else:
            print("Token hasn't changed. Skipping update.")
    else:
        print("Could not find a valid token in the source string.")

# Run the script
if __name__ == "__main__":
    response = requests.get(STATUS_URL, timeout=(0.5))
    responseText = response.text

^G Help          ^O Write Out     ^W Where Is      ^K Cut           ^T Execute       ^C Location      M-U Undo         M-A Set Mark
^X Exit          ^R Read File     ^\ Replace       ^U Paste         ^J Justify       ^/ Go To Line    M-E Redo         M-6 Copy
