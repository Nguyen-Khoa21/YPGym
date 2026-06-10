import os


def main() -> None:
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    device_id = os.getenv("IOT_DEVICE_ID", "local-simulator-1")
    print(f"YPGym IoT simulator placeholder ready for {api_base_url} as {device_id}.")


if __name__ == "__main__":
    main()
