import unittest
from main import setup_services, Arguments
from multiprocessing import Queue
import os

# this is bad, but I can't figure out how to import config mypy complaining
import config  # type: ignore


class TestLifespan(unittest.IsolatedAsyncioTestCase):
    async def test_setup_services(self):
        config_path = os.path.join(os.path.dirname(__file__), "test_data", "config.json")
        args = Arguments(config=config_path, port=config.PORT)
        for service in await setup_services(args, Queue()):
            self.assertTrue(service is not None)


if __name__ == "__main__":
    unittest.main()
