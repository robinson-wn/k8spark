# https://github.com/jupyter/notebook/blob/6.4.x/notebook/notebookapp.py
# Consider adding extensions
# https://towardsdatascience.com/jupyter-notebook-extensions-517fa69d2231

import os
import sys
from uuid import uuid4


from notebook.notebookapp import NotebookApp

__name__ = "jupyter"

if "JUPYTER_PORT" in os.environ:
    PORT = os.environ['JUPYTER_PORT']
else:
    PORT = 8888
TOKEN = str(uuid4())


# https://stackoverflow.com/questions/66046154/cant-access-jupyter-notebook-in-docker-mac
def nb_server(port=PORT, token=TOKEN):
    print("Jupyter notebook token: {}".format(token))
    app = NotebookApp()
    app.initialize(["--port", f"{port}",
                    "--ip", "0.0.0.0",
                    f"--NotebookApp.token={token}",
                    "--allow-root",
                    "--no-browser"])
    app.start()


def main():
    print(f"hidden token {TOKEN}", file=sys.stderr)
    nb_server(port=PORT, token=TOKEN)
