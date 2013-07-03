# We need to monkey_patch everything
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, Response, stream_with_context, jsonify
from gevent import pywsgi
import gevent
import redis
import json


app = Flask(__name__)
# Replace with localhost or your hostname if you're running
# redis locally.
r = redis.StrictRedis('jpanganiban-dev')


@app.route('/chat', methods=['GET', 'POST'])
def api_chat():
    """Streaming chat api"""

    if request.method == 'GET':
        stream_type = request.headers.get('accept')

        def stream(stream_type):
            # Create a pubsub instance
            pubsub = r.pubsub()
            # Subscribe specifically to this namespace
            pubsub.subscribe('chat')
            # Start listening to stuff being transmitted
            # here.
            for data in pubsub.listen():
                # Data is usually string.
                if not isinstance(data['data'], str):
                    continue
                # Make sure that the data is valid json.
                data = json.loads(data['data'])

                # Dump data according to stream_type
                # requested.
                if stream_type == 'text/event-stream':
                    yield "data: %s\n\n" % json.dumps(data)
                else:
                    yield "%s\n" % json.dumps(data)

                # Sleep to work on a different thing
                gevent.sleep(0)

        headers = {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
        }
        # Respond to as streaming data
        return Response(stream_with_context(stream(stream_type)), headers=headers)

    if request.method == 'POST':
        # Let's fetch the form-encoded data.
        data = request.form.to_dict()
        # Check if the necessary data is in the request.
        if not data.get('message', None):
            return jsonify({'error': 'Required data: message'}), 400
        # Set default alias
        data['alias'] = data.get('alias', 'anonymous')
        # Publish a message
        r.publish('chat', json.dumps(data))
        return jsonify(data)


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()

    #gevent.joinall([
    #    gevent.spawn(server.serve_forever),
    #])
