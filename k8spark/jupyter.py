import os

from k8spark import logger


def main():
    logger.info("Starting Jupyter Server")
    bash_script = """
    echo "--- Starting JupyterLab via Bash Bridge ---"
    export JUPYTER_PORT=${JUPYTER_PORT:-8888}
    
    exec jupyter lab \
        --ip=0.0.0.0 \
        --port=$JUPYTER_PORT \
        --no-browser \
        --allow-root \
        --NotebookApp.token='' \
        --NotebookApp.password='' \
        --notebook-dir=/opt/spark/work-dir
    """

    # This replaces the Python process with a Bash process running the string above
    os.execvp("bash", ["bash", "-c", bash_script])


if __name__ == "__main__":
    main()
