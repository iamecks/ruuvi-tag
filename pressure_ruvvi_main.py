import sys
import logging
import asyncio
import aioconsole
import pressure_ruvvi_lib as pr
import select
import inputimeout
import time
import os


async def ruuvi(n):
    """
    Main function to connect to Ruuvi devices, subscribe to notifications, and handle disconnections.
    """

    # Set up logging
    setup_logging()

    # Find all devices
    device_info = await pr.find_all_devices(n)

    # Connect to all devices and subscribe to notifications
    clients, clients_address, disconnected_address = await connect_and_subscribe(device_info)

    # Monitor for user input and handle disconnections
    user_input = await monitor_user_input_and_handle_disconnections(clients, clients_address, disconnected_address, device_info)

    return user_input


def setup_logging():
    """
    Set up logging to both a file and stdout.
    """
    file_handler = logging.FileHandler(filename='pressure_ruvvi_log.txt', mode='w')
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [file_handler, stdout_handler]
    logging.basicConfig(handlers=handlers, level=logging.INFO)
    logging.getLogger('bleak.backends.winrt.client').disabled = True


async def connect_and_subscribe(device_info):
    """
    Connect to all devices and subscribe to notifications.
    """
    clients = []
    clients_address = []
    disconnected_address = []

    for device in device_info:
        client = await pr.try_until_connect(device, disconnected_address)
        clients.append(client)
        clients_address.append(client.address)
        await pr.subscribe_notification(client)

    return clients, clients_address, disconnected_address


async def monitor_user_input_and_handle_disconnections(clients, clients_address, disconnected_address, device_info):
    """
    Monitor for user input and handle disconnections.
    """
    total_time = 0

    while True:
        start_time = time.time()

        if disconnected_address:
            await handle_disconnection(clients, clients_address, disconnected_address, device_info)
        else:
            try:
                user_input = inputimeout.inputimeout(prompt=f"duration: {int(total_time)}", timeout=0.001)

                for client in clients:
                    await client.disconnect()
                break

            except inputimeout.TimeoutOccurred:
                pass

            await asyncio.sleep(1)

        end_time = time.time()
        total_time += (end_time - start_time)

    return user_input


async def handle_disconnection(clients, clients_address, disconnected_address, device_info):
    """
    Handle a disconnection by reconnecting and subscribing to notifications.
    """
    disconnected_address = disconnected_address.pop()
    index = clients_address.index(disconnected_address)

    # Re-order addresses
    clients_address.append(clients_address.pop(index))
    device_info.append(device_info.pop(index))

    del(clients[index])

    # Reconnect
    client = await pr.try_until_connect(device_info[-1], disconnected_address)
    clients.append(client)

    await pr.subscribe_notification(client)