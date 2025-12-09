from ytmusicapi.setup import setup_oauth

if __name__ == "__main__":
    print("="*50)
    print("   🔑  YouTube Music OAuth Setup  🔑")
    print("="*50)
    print("This will open a link to authorize the application.")
    print("Follow the steps in your browser and paste the code if requested.")
    print("-" * 50)
    
    try:
        # This function handles the entire flow and saves oauth.json
        setup_oauth(client_secrets="client_secrets.json", credentials="oauth.json")
        print("\n✅ Success! OAuth credentials saved to 'oauth.json'.")
        print("You can now deletions 'headers_auth.json' if you wish.")
        print("Try: python cli.py scan")
    except Exception as e:
        print(f"\n❌ Error during OAuth setup: {e}")
