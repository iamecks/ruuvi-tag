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

    # Logging config
    file_handler = logging.FileHandler(filename='pressure_ruvvi_log.txt', mode='w')
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [file_handler, stdout_handler]
    logging.basicConfig(handlers=handlers, level=logging.INFO)
    logging.getLogger('bleak.backends.winrt.client').disabled = True

    # Get number of devices expected
    # n_devices = int(sys.argv[1])

    # Find address of all devices
    
    # logging.info(f' Expected number of devices: {n}')
    device_info = await pr.find_all_devices(n)
        
    # Test connections
    # await pr.test_all_connections(device_info)

    # Info
    clients = []
    clients_address = []
    disconnected_address = []

    # Loop to connect all devices
    for d in device_info:
        c = await pr.try_until_connect(d, disconnected_address)
        clients.append(c)
        # document client address
        clients_address.append(c.address)

    # subscribe_notification
    for c in clients:
            await pr.subscribe_notification(c)

    # scan for user input to stop and check for disconnection
    t = 0
    while True:
        
        start = time.time()
        if disconnected_address:

            # pop out current disconnected address
            da = disconnected_address.pop()
            ind = clients_address.index(da)

            # re-ordering address order
            clients_address.append(clients_address.pop(ind))
            device_info.append(device_info.pop(ind))

            del(clients[ind])

            # reconnection
            c = await pr.try_until_connect(device_info[-1], disconnected_address)
            clients.append(c)

            await pr.subscribe_notification(c)           
        
        else:

            # Check if there is a user input 
            try:
                line = inputimeout.inputimeout(prompt = ("duration:"+ str(t)), timeout = 0.001)
                
                for c in clients:
                    await c.disconnect()
                break

            except inputimeout.TimeoutOccurred:
                pass 
            
            # wait for 1 sec
            await asyncio.sleep(1)
        end = time.time()
        t = t+(end-start)

    return line