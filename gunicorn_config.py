import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
backlog = 2048

# Worker processes
workers = 2  # Rule of thumb: 2-4 x $(NUM_CORES)
worker_class = 'sync'
worker_connections = 1000
timeout = 300  # 5 minutes
keepalive = 2

# Process naming
proc_name = 'property-log'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Memory management
max_requests = 1000  # Restart workers after this many requests
max_requests_jitter = 50  # Add randomness to max_requests
worker_tmp_dir = "/dev/shm"  # Use RAM for temp files
worker_exit_on_memory = 512  # MB - restart worker if memory exceeds this
worker_abort_on_memory = 1024  # MB - kill worker if memory exceeds this

# Preload app for better performance
preload_app = True

def post_worker_init(worker):
    """Called just after a worker has been initialized."""
    import gc
    gc.enable()  # Enable garbage collection
    gc.set_threshold(100, 5, 5)  # More aggressive GC

def worker_exit(server, worker):
    """Called just after a worker has been killed."""
    import gc
    gc.collect()  # Force final garbage collection

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    import gc
    gc.collect()  # Collect garbage before each request

def post_request(worker, req, environ, resp):
    """Called just after a worker processes the request."""
    import gc
    gc.collect()  # Collect garbage after each request
