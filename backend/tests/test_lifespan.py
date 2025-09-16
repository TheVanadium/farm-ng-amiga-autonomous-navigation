import unittest
from main import setup_services
from multiprocessing import Queue
import os
from argparse import Namespace
import config


class TestLifespan(unittest.IsolatedAsyncioTestCase):
    async def test_setup_services(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "test_data", "config.json"
        )
        args = Namespace(config=config_path, port=config.PORT)
        for service in await setup_services(args, Queue()):
            self.assertTrue(service is not None)


if __name__ == "__main__":
    unittest.main()
