import json

def parse_raw_headers(input_file, output_file):
    headers = {}
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    raw_headers = {}
    for i in range(0, len(lines), 2):
        if i + 1 < len(lines):
            key = lines[i]
            value = lines[i+1]
            if key.startswith(':'):
                key = key[1:]
            raw_headers[key.lower()] = value
            
    # Filter for essential headers
    # We need cookie, x-goog-authuser, x-origin.
    # User-Agent is good to have.
    # Authorization is good.
    # We MUST remove content-length, host, accept-encoding (let requests handle these)
    
    essential_keys = [
        'cookie',
        'x-goog-authuser',
        'x-origin',
        'user-agent',
        'authorization',
        'accept-language'
    ]
    
    clean_headers = {}
    for key in essential_keys:
        if key in raw_headers:
            clean_headers[key] = raw_headers[key]
            
    # Add x-youtube-client-version if present, it's important for the API version
    if 'x-youtube-client-version' in raw_headers:
        clean_headers['x-youtube-client-version'] = raw_headers['x-youtube-client-version']
    if 'x-youtube-client-name' in raw_headers:
        clean_headers['x-youtube-client-name'] = raw_headers['x-youtube-client-name']

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clean_headers, f, indent=4)
    
    print(f"Successfully created {output_file} with {len(clean_headers)} headers.")

if __name__ == "__main__":
    parse_raw_headers('raw_headers.txt', 'headers_auth.json')
