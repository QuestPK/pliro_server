import os
import redis
from rq import Worker, Queue
from redis import Redis

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
conn = Redis.from_url(redis_url)

if __name__ == "__main__":
    # Create queues with the connection
    default_queue = Queue("default", connection=conn)

    # Create worker with the queues
    worker = Worker([default_queue], connection=conn)
    worker.work()