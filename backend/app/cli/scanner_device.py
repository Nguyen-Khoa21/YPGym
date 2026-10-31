import argparse
import asyncio
from getpass import getpass

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.attendance import IoTDevice
from app.utils.security import hash_token


async def provision(device_id: str, display_name: str) -> None:
    api_key = getpass("Device API key (input is hidden): ")
    confirmation = getpass("Confirm device API key: ")
    if len(api_key) < 24:
        raise SystemExit("The device API key must be at least 24 characters.")
    if api_key != confirmation:
        raise SystemExit("The device API key confirmation did not match.")
    async with AsyncSessionLocal() as session:
        device = (
            await session.execute(select(IoTDevice).where(IoTDevice.device_id == device_id))
        ).scalar_one_or_none()
        if device:
            device.display_name = display_name
            device.api_key_hash = hash_token(api_key)
            device.is_active = True
            action = "rotated and activated"
        else:
            session.add(
                IoTDevice(
                    device_id=device_id,
                    display_name=display_name,
                    api_key_hash=hash_token(api_key),
                    is_active=True,
                ),
            )
            action = "provisioned"
        await session.commit()
    print(f"Scanner device {device_id!r} was {action}. The API key was not printed or stored in plaintext.")


async def revoke(device_id: str) -> None:
    async with AsyncSessionLocal() as session:
        device = (
            await session.execute(select(IoTDevice).where(IoTDevice.device_id == device_id))
        ).scalar_one_or_none()
        if not device:
            raise SystemExit(f"Scanner device {device_id!r} was not found.")
        device.is_active = False
        await session.commit()
    print(f"Scanner device {device_id!r} was revoked.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision or revoke a YPGym scanner device.")
    commands = parser.add_subparsers(dest="command", required=True)
    provision_parser = commands.add_parser("provision")
    provision_parser.add_argument("device_id")
    provision_parser.add_argument("display_name")
    revoke_parser = commands.add_parser("revoke")
    revoke_parser.add_argument("device_id")
    args = parser.parse_args()
    if args.command == "provision":
        asyncio.run(provision(args.device_id, args.display_name))
    else:
        asyncio.run(revoke(args.device_id))


if __name__ == "__main__":
    main()
