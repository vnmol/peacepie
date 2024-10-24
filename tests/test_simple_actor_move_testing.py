import asyncio
import os
import sys
import unittest
import multiprocessing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import peacepie


multiprocessing.set_start_method('spawn', force=True)


class TestSimple(unittest.TestCase):

    async def simple(self):
        pp = peacepie.PeaceSystem('./config/test_simple_actor_move_testing.cfg')
        await pp.start()
        try:
            await pp.task
        except asyncio.CancelledError:
            pass
        return pp

    def test_simple(self):
        pp = asyncio.run(self.simple())
        for res in pp.test_errors:
            self.assertTrue(False, res.get('msg'))


if __name__ == '__main__':
    unittest.main()
