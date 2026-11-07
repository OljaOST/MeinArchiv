from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/dokumente")
def dokumente():
    return app.send_static_file("dokumente.html")