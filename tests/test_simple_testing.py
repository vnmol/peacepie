import asyncio
import unittest
import multiprocessing

import peacepie


multiprocessing.set_start_method('spawn', force=True)


class TestSimple(unittest.TestCase):

    async def simple(self):
        pp = peacepie.PeaceSystem('./config/test_simple_testing.cfg')
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
