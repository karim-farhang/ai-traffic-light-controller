import asyncio
import socket

async def send_command(client_socket, command):
    client_socket.send(command.encode('utf-8'))
    print(f"Sent command: {command}")

async def control_lights(client_socket):
    try:
        while True:
            # User selects which light to turn on green
            selected_light = input("Enter the light number to turn green (1-4): ")

            # First, turn off all types of lights for all lights
            for light_type in ['red', 'green', 'yellow']:  # Add more types if needed
                for i in range(1, 5):
                    await send_command(client_socket, f"light{i}_{light_type}_off")
                    await asyncio.sleep(0.1)  # Short delay between turning off each light

            # Turn on green light for the selected light
            command = f"light{selected_light}_green_on"
            await send_command(client_socket, command)

            # Turn on red lights for the other lights
            for i in range(1, 5):
                if str(i) != selected_light:
                    red_command = f"light{i}_red_on"
                    await send_command(client_socket, red_command)
                    await asyncio.sleep(0.1)  # Short delay between sending each command

            if command.lower() == 'exit':
                print("Closing connection...")
                break

            await asyncio.sleep(1)  # Adding a sleep to avoid rapid firing of commands
    except KeyboardInterrupt:
        print("\nClient is shutting down...")

async def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = '192.168.1.203'  # Replace with the Raspberry Pi's IP address
    port = 9999

    await asyncio.get_event_loop().run_in_executor(None, client_socket.connect, (host, port))
    print(f"Connected to server at {host}:{port}")

    try:
        await control_lights(client_socket)
    finally:
        client_socket.close()

# Entry point for the async client
asyncio.run(start_client())
