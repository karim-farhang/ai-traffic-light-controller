import socket

def start_client():
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Define the server address and port
    host = 'localhost'
    port = 9999

    # Connect to the server
    client_socket.connect((host, port))

    try:
        while True:
            # Receive the message from the server
            message = client_socket.recv(1024).decode('utf-8')

            if not message:
                # If the message is empty, the server has likely closed the connection
                print("Connection closed by the server.")
                break

            print(f"Message from server: {message}")
    except KeyboardInterrupt:
        print("\nClient is shutting down...")
    finally:
        # Close the connection
        client_socket.close()

if __name__ == "__main__":
    start_client()
