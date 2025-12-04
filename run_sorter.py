from sorter import PlaylistManager
import time

def main():
    pm = PlaylistManager()
    
    # Playlist IDs
    shazam_id = "PLbdOfJbnzIMBjcRlHJTEG5Ls54YjPHrXl"
    
    targets = {
        "Future Funk": "PLbdOfJbnzIMCfc_ALLTTIZNACr26UkKSa",
        "Anime & Japan": "PLbdOfJbnzIMBL15USa4PX-QpZeMTpaO6u",
        "Pop Mix": "PLbdOfJbnzIMDzYPZJtDgKF4Y6TDQOqVnY",
        "Gaming & OST": "PLbdOfJbnzIMD1S2H6-8O_KW19XRcG6RIC",
        "Rock & Prog": "PLbdOfJbnzIMD8n12vOULbpKumAv_QuyKr",
        "Mood: Sad/Slow": "PLbdOfJbnzIMBFM-9vfHWQu7yUZ5TxSLRN",
        "Hip-Hop & Alt": "PLbdOfJbnzIMB53024PpV6_8f4Bx8ID6Ki",
        "Phonk & Drive": "PLbdOfJbnzIMCP_xfHzRY6w1sA52UjKc7A",
        "Focus & Lo-Fi": "PLbdOfJbnzIMDfabjaf1INFsK-TBKeBaR3"
    }
    
    all_playlists = list(targets.values()) + [shazam_id]
    
    # print("=== STEP 1: Smart Organization (Shazam -> Targets) ===")
    # try:
    #     pm.smart_organize(shazam_id, list(targets.values()))
    # except Exception as e:
    #     print(f"Smart sort failed: {e}")

    # print("\n=== STEP 2: Deduplication ===")
    # for name, pid in targets.items():
    #     print(f"Deduplicating {name}...")
    #     try:
    #         pm.deduplicate_playlist(pid)
    #     except Exception as e:
    #         print(f"Failed to dedup {name}: {e}")
            
    # print("Deduplicating Shazam...")
    # try:
    #     pm.deduplicate_playlist(shazam_id)
    # except Exception as e:
    #     print(f"Failed to dedup Shazam: {e}")

    print("\n=== STEP 3: Sorting (Creating Copies) ===")
    for name, pid in targets.items():
        print(f"Sorting {name}...")
        try:
            pm.sort_standard(pid, create_copy=True)
        except Exception as e:
            print(f"Failed to sort {name}: {e}")
            
    print("Sorting Shazam...")
    try:
        pm.sort_standard(shazam_id, create_copy=True)
    except Exception as e:
        print(f"Failed to sort Shazam: {e}")

    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
