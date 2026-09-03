from access_core import register_device


def main():
    print("\n=== OrchardEye Device Registration ===")
    print("Register a trap device and generate its upload API key.\n")

    trap_id = input("Trap ID (e.g. TRAP_05): ").strip()
    district = input("District: ").strip()
    village = input("Village: ").strip()
    latitude = input("Latitude: ").strip()
    longitude = input("Longitude: ").strip()

    if not all([trap_id, district, village, latitude, longitude]):
        print("All fields are required.")
        return

    try:
        result = register_device(
            trap_id=trap_id,
            district=district,
            village=village,
            latitude=float(latitude),
            longitude=float(longitude),
            active=True,
        )
    except ValueError as exc:
        print(exc)
        return
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return

    print("\nDevice registered successfully")
    print(f"Trap ID : {result['trap_id']}")
    print(f"API Key : {result['api_key']}")
    print("\nConfigure the trap firmware with this API key for POST /upload.")


if __name__ == "__main__":
    main()
