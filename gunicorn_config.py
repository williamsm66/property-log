# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

def on_starting(server):
    """Log when Gunicorn starts."""
    logger.info("Gunicorn is starting up")
    logger.info(f"Workers: {workers}")
    logger.info(f"Worker class: {worker_class}")
    logger.info(f"Timeout: {timeout}")

def on_reload(server):
    """Log when Gunicorn reloads."""
    logger.info("Gunicorn worker reload")

def when_ready(server):
    """Log when Gunicorn is ready."""
    logger.info("Gunicorn server is ready. Listening on: %s", bind)

def worker_int(worker):
    """Log when worker receives INT or QUIT signal."""
    logger.info(f"Worker {worker.pid} received INT or QUIT signal")

def worker_abort(worker):
    """Log when worker receives SIGABRT signal."""
    logger.error(f"Worker {worker.pid} received SIGABRT signal")

def post_worker_init(worker):
    """Called just after a worker has been initialized."""
    logger.info(f"Worker {worker.pid} initialized")
    try:
        import psutil
        process = psutil.Process()
        logger.info(f"Worker memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    except ImportError:
        logger.info("psutil not installed - skipping memory logging")

def worker_exit(server, worker):
    """Called just after a worker has been killed."""
    logger.info(f"Worker {worker.pid} exited")
    try:
        import psutil
        process = psutil.Process()
        logger.info(f"System memory available: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
    except ImportError:
        pass

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    logger.debug(f"Worker {worker.pid} processing request: {req.uri}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    logger.debug(f"Worker {worker.pid} completed request: {req.uri} - Status: {resp.status}")