"""
WebSocket consumers for the core application.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ResearchSession

class ResearchConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for research sessions."""
    
    async def connect(self):
        """Handle connection to the WebSocket."""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"research_{self.session_id}"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Check if session exists and send initial status
        session = await self.get_session()
        if session:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'data': {
                    'stage': session['status'],
                    'message': f"Connected to session {self.session_id}"
                }
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'data': {
                    'stage': 'error',
                    'message': f"Session {self.session_id} not found"
                }
            }))
    
    async def disconnect(self, close_code):
        """Handle disconnection from the WebSocket."""
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages received from the WebSocket."""
        try:
            data = json.loads(text_data)
            
            # If client sends a ping, respond with pong
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp', 0)
                }))
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Error processing message: {str(e)}"
            }))
    
    # Handlers for different message types
    async def status_message(self, event):
        """Send status message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': event['data']
        }))
    
    async def result_message(self, event):
        """Send result message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'result',
            'data': event['data']
        }))
    
    async def error_message(self, event):
        """Send error message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event['message']
        }))
    
    @database_sync_to_async
    def get_session(self):
        """Get the session from the database."""
        try:
            session = ResearchSession.objects.filter(id=self.session_id).values().first()
            return session
        except Exception:
            return None

class TestWebSocketConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for testing WebSocket functionality."""
    
    async def connect(self):
        """Handle connection to the WebSocket."""
        self.group_name = "websocket_test"
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': {
                'stage': 'connected',
                'message': "WebSocket connection successful"
            }
        }))
    
    async def disconnect(self, close_code):
        """Handle disconnection from the WebSocket."""
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Echo back any received messages for testing."""
        try:
            data = json.loads(text_data)
            
            # Echo the message back
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'data': data,
                'message': "Echo response from server"
            }))
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f"Error processing message: {str(e)}"
            }))
    
    # Handlers for different message types
    async def status_message(self, event):
        """Send status message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': event['data']
        }))
    
    async def echo_message(self, event):
        """Echo a message to the WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'echo',
            'data': event['data']
        }))
