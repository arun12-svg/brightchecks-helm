import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://10.0.0.102:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "brightchecks")

    # RabbitMQ
    RABBITMQ_URI = os.getenv("RABBITMQ_URI", "amqp://guest:guest@10.0.0.101:5672//")

    # Collections
    TESTCASES_COLLECTION = "testcases"
    EXECUTIONS_COLLECTION = "testcase_execution"

config = Config()
