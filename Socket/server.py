import socket


def start_server():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Get local machine name or use 'localhost'
    host = 'localhost'
    port = 9999

    # Bind the socket to a public host and a port
    server_socket.bind((host, port))

    # Listen for incoming connections (1 client at a time)
    server_socket.listen(1)

    print(f"Server is listening on {host}:{port}...")

    # Accept a connection
    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr} has been established!")

    try:
        while True:
            # Get input from the server user
            message = input("Enter message to send to the client: ")

            # Send the message to the client
            client_socket.send(message.encode('utf-8'))

            # Optional: Break the loop if a specific message is sent
            if message.lower() == 'exit':
                print("Server is shutting down...")
                break
    except KeyboardInterrupt:
        print("\nServer is shutting down...")
    finally:
        # Close the connection with the client
        client_socket.close()
        server_socket.close()


if __name__ == "__main__":
    start_server()
