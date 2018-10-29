import conf

from werkzeug import serving
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
    # , version = '1.38'
    dockerCli = ClientHandler(base_url=conf.DOCKER_HOST, timeout=10)
    terminalExecId = dockerCli.creatTerminalExec(conf.CONTAINER_ID)
    terminalStream = dockerCli.startTerminalExec(terminalExecId)._sock

    terminalThread = DockerStreamThread(ws, terminalStream)
    terminalThread.start()
    beat_thread = BeatWS(ws, dockerCli.client)
    beat_thread.start()

    try:
        while not ws.closed:
            message = ws.receive()
            if message is not None:
                sed_msg = bytes(message, encoding='utf-8')
                if sed_msg != b'__ping__':
                    terminalStream.send(bytes(message, encoding='utf-8'))
    except Exception as err:
        print(err)
    finally:
        ws.close()
        terminalStream.close()
        dockerCli.dockerClient.close()


@serving.run_with_reloader
def run_server():
    app.debug = True
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(
        listener=('0.0.0.0', 5000),
        application=app,
        handler_class=WebSocketHandler)
    server.serve_forever()


if __name__ == '__main__':
    run_server()
