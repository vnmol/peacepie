import json

from . import zmq_client


async def websocket_application(scope, receive, send):
    while True:
        event = await receive()
        if event['type'] == 'websocket.connect':
            await send({'type': 'websocket.accept'})
        if event['type'] == 'websocket.disconnect':
            break
        if event['type'] == 'websocket.receive':
            ans = zmq_client.client.send_request(json.loads(event['text']))
            if ans.get('is_text'):
                text = ans.get('text')
            else:
                text = json.dumps(ans)
            await send({'type': 'websocket.send', 'text': text})