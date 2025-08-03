#!/usr/bin/env python

"""
Simple test to verify sound monitoring logic
"""

import json
import socket
import time

def test_mpv_socket_communication():
    """Test communication with mpv socket"""
    try:
        # Create a test socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        sock.connect('/tmp/mpvsocket')
        
        # Send test command
        command = '{"command": ["get_property", "idle-active"]}\n'
        sock.send(command.encode())
        
        response = sock.recv(1024).decode()
        sock.close()
        
        print(f"Response: {response}")
        
        # Parse response
        data = json.loads(response)
        idle_active = data.get('data', False)
        print(f"Idle active: {idle_active}")
        
        return idle_active
        
    except Exception as e:
        print(f"Socket test failed: {e}")
        return None

if __name__ == "__main__":
    print("Testing mpv socket communication...")
    result = test_mpv_socket_communication()
    print(f"Test result: {result}") 