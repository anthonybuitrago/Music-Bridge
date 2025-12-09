import json
import os

def setup_auth():
    print("="*50)
    print("   🔑  YouTube Music Auth Setup  🔑")
    print("="*50)
    print("\nTo access your private library, we need your browser 'Cookie' and authentication headers.")
    print("This allows the app to act as 'you' on YouTube Music.\n")
    
    print("INSTRUCTIONS:")
    print("1. Open https://music.youtube.com in Google Chrome or Edge.")
    print("2. Open Developer Tools (F12) and go to the 'Network' tab.")
    print("3. Browse to any page (e.g. Library) so requests appear.")
    print("4. Click on any request starting with 'browse' or 'music_app'.")
    print("5. Look for 'Request Headers' on the right panel.")
    print("6. Copy everything under 'Request Headers' (or specifically the 'Cookie' and 'Authorization' if you know how).")
    print("   Tip: You can usually right-click the request -> Copy -> Copy Request Headers.")
    print("-" * 50)
    
    print("\nPaste the headers below. When finished, press ENTER twice (or input 'END'):\n")
    
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == 'END' or (not line and lines and not lines[-1]):
             # Stop on explicit END or double newline
             break
        lines.append(line)
        
    raw_data = "\n".join(lines)
    
    if not raw_data.strip():
        print("❌ No data entered. Exiting.")
        return

    # Parse headers
    headers = {}
    
    # Check if user pasted JSON directly
    try:
        if raw_data.strip().startswith('{'):
            headers = json.loads(raw_data)
            print("✅ Detected JSON format.")
    except:
        pass
        
    if not headers:
        # Parse raw HTTP headers
        for line in raw_data.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        
        # Fallback: Check if the raw data itself looks like a cookie string
        # (User pasted 'SID=...; SAPISID=...' directly, possibly with quotes)
        if 'Cookie' not in headers and 'cookie' not in headers:
            # Strip quotes if present (e.g. from copy-pasting JS console string)
            cleaned = raw_data.strip().strip("'").strip('"')
            if 'SAPISID=' in cleaned or 'SID=' in cleaned:
                print("✅ Detected raw cookie string.")
                headers['Cookie'] = cleaned
                
    # Validate
    if 'Cookie' not in headers and 'cookie' not in headers:
         print("\n⚠️ WARNING: No 'Cookie' found in headers. Authentication will likely fail.")
         confirm = input("Save anyway? (y/n): ")
         if confirm.lower() != 'y':
             return
             
    # Save
    try:
        with open('headers_auth.json', 'w') as f:
            json.dump(headers, f, indent=4)
        print(f"\n✅ Success! Saved to 'headers_auth.json'.")
        print("Try running 'python cli.py scan' again.")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

if __name__ == "__main__":
    setup_auth()
