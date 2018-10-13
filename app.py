import conf

from flask_sockets import Sockets
from flask import Flask, render_template
from utility.myDocker import ClientHandler, DockerStreamThread, BeatWS


app = Flask(__name__)
sockets = Sockets(app)


@app.route('/')
def index():
    return render_template('index.html')


@sockets.route('/echo')
def echo_socket(ws):
    dockerCli = ClientHandler(base_url=conf.DOCKER_HOST, timeout=10, version='1.38')
    terminalExecId = dockerCli.creatTerminalExec(conf.CONTAINER_ID)
    terminalStream = dockerCli.startTerminalExec(terminalExecId)._sock

    terminalThread = DockerStreamThread(ws, terminalStream)
    terminalThread.start()
    beat_thread = BeatWS(ws, dockerCli.client)
    beat_thread.start()

    while not ws.closed:
        message = ws.receive()
        if message is not None:
            sed_msg = bytes(message, encoding='utf-8')
            if sed_msg != b'__ping__':
                terminalStream.send(bytes(message, encoding='utf-8'))

    terminalStream.send(bytes('exit\n', encoding='utf-8'))
    dockerCli.dockerClient.close()
    terminalThread.start()


if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
