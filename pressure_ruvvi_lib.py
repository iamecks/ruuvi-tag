import sys
from functools import partial
import logging
import asyncio
from time import time
import struct
from typing import Sequence
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
import select
import os


async def find_all_devices(n_devices):
    """
    Find all devices.
    A single scan cannot find all devices.
    Loop to scan until n devices are found.
    """
    device_addr = []
    device_info = []

    while True:
        n_before = len(device_addr)
        devices = await BleakScanner.discover(timeout=10.0)

        for device in devices:
            if device.name and 'Ruuvi' in device.name and device.address not in device_addr:
                device_addr.append(device.address)
                device_info.append(device)

                logging.info(f' {len(device_addr)} out of {n_devices} devices found. Device address: {device_addr[-1]}')

                if len(device_addr) == n_devices:
                    logging.info(f' All devices found.')
                    return device_info

        if len(device_addr) == n_before:
            logging.error(f' No new device found, scanning again.')


def handle_disconnect(disconnected_address, client: BleakClient):
    """
    Log disconnection.
    """
    logging.info(f' Device {client.address} was disconnected.')
    disconnected_address.append(client.address)


async def try_until_connect(device_info, disconnected_address):
    """
    Device cannot be found all the time.
    Loop to until the device is connected successfully.
    """
    client = BleakClient(device_info, timeout=10.0, disconnected_callback=partial(handle_disconnect, disconnected_address))
    not_found = True

    while not_found:
        try:
            await client.connect()
            not_found = False
            logging.info(f' Device {device_info.address} connected.')
        except Exception as e:
            logging.error(f' Device {device_info.address} was not found. Trying again.')

    return client


async def test_all_connections(device_info):
    """
    Test if devices can be connected.
    """
    for device in device_info:
        client = await try_until_connect(device)
        await client.disconnect()


def handle_rx_with_client(client: BleakClient, sender: int, data: bytearray):
    """
    Handle received data with client.
    """
    time_stamp = str(time())
    data_ascii = ','.join(map(str, struct.unpack('f'*31+'i', data)))

    with open(client.address.replace(':','-') + '.csv', 'a') as f:
        f.write(time_stamp + ',' + data_ascii + '\n')


async def subscribe_notification(client):
    """
    Subscribe to notifications from the client.
    """
    await client.start_notify('6E400003-B5A3-F393-E0A9-E50E24DCCA9E', partial(handle_rx_with_client, client))
    logging.info(f' Device {client.address} begins data acquisition.')


async def stop_notification(client):
    """
    Stop notifications from the client.
    """
    await client.stop_notify('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
    logging.info(f'Device {client.address} stops data acquisition.')