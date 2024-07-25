import asyncio
import unittest
import multiprocessing

import peacepie


multiprocessing.set_start_method('spawn', force=True)


class TestSimple(unittest.TestCase):

    async def separate_channel(self):
        pp = peacepie.PeaceSystem('./config/test_simple_navi_testing.cfg',
                                  {'is_embedded_channel': False})
        await pp.start()
        try:
            await pp.task
        except asyncio.CancelledError:
            pass
        return pp

    async def embedded_channel(self):
        pp = peacepie.PeaceSystem('./config/test_simple_navi_testing.cfg',
                                  {'is_embedded_channel': True})
        await pp.start()
        try:
            await pp.task
        except asyncio.CancelledError:
            pass
        return pp

    def test_separate_channel(self):
        pp = asyncio.run(self.separate_channel())
        for res in pp.test_errors:
            self.assertTrue(False, res.get('msg'))

    def test_embedded_channel(self):
        pp = asyncio.run(self.embedded_channel())
        for res in pp.test_errors:
            self.assertTrue(False, res.get('msg'))


if __name__ == '__main__':
    unittest.main()
