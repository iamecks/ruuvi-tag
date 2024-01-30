import sys
from functools import partial
import logging
import asyncio
from time import time
import struct
from typing import Sequence
from bleak import BleakScanner,BleakClient
from bleak.backends.device import BLEDevice
import select
import os

async def find_all_devices(n_devices):
    '''Find all devices
    A single scan cannot find all devices
    Loop to scan until n devices are found
    '''
    # Empty list to store name and address of Ruuvi tags
    device_addr = []
    device_info = []

    # If number of devices do not match # of devices expected, keep scanning
    while True:
        # Remember current number of devices found
        n_before = len(device_addr)

        # Discover all nearby devices
        devices = await BleakScanner.discover(timeout=10.0)
        
        # Loop through all devices
        for d in devices:
            if d.name:
                if 'Ruuvi' in d.name and d.address not in device_addr:
                    device_addr.append(d.address)
                    device_info.append(d)

                    # Logging
                    logging.info(f' {len(device_addr)} out of {n_devices} devices found. Device address: {device_addr[-1]}')

                    # Check if all devices are found
                    if len(device_addr) == n_devices:
                        logging.info(f' All devices found.')
                        return device_info

        # If no new device found
        if len(device_addr) == n_before: logging.error(f' No new device found, scanning again.')

# Simple function to log disconnection
def handle_disconnect(disconnected_address, client:BleakClient):
    logging.info(f' Device {client.address} was disconnected.')
    disconnected_address.append(client.address)

async def try_until_connect(device_info, disconnected_address):
    '''Device cannot be found all the time.
    Loop to until the device is connected successfully
    '''
    # Create BLE client
    client = BleakClient(device_info, timeout=10.0, disconnected_callback=partial(handle_disconnect, disconnected_address))
    
    not_found = True

    # Try until that particular device is found
    while not_found:
        try:
            await client.connect()
            not_found = False
            logging.info(f' Device {device_info.address} connected.')
        except Exception as e:
            logging.error(f' Device {device_info.address} was not found. Trying again.')

    return client

async def test_all_connections(device_info):
    '''Test if devices can be connected.
    '''
    # Loop through all devices
    for d in device_info:

        # Create client
        client = await try_until_connect(d)

        # Disconnect client
        await client.disconnect()

def handle_rx_with_client(client: BleakClient, sender: int, data: bytearray):
    
    
    time_stamp = str(time())
    data_ascii = ','.join(map(str,struct.unpack('f'*31+'i', data)))

    with open(client.address.replace(':','-') + '.csv', 'a') as f:
        f.write(time_stamp + ',' + data_ascii + '\n')

async def subscribe_notification(client):
    await client.start_notify('6E400003-B5A3-F393-E0A9-E50E24DCCA9E', partial(handle_rx_with_client, client))
    logging.info(f' Device {client.address} begins data acquisition.')

async def stop_notification(client):
    '''Do not use. Windows bug crash program'''
    await client.stop_notify('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
    logging.info(f'Device {client.address} stops data acquisition.')
