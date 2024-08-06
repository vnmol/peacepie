import asyncio
import unittest
import multiprocessing
from playwright.async_api import async_playwright

import peacepie


multiprocessing.set_start_method('spawn', force=True)


class TestSimpleWebFace(unittest.TestCase):

    async def simple_web_face(self):
        pp = peacepie.PeaceSystem('./config/test_simple_web_face.cfg')
        await pp.start()
        try:
            async with async_playwright() as playwright:
                await run(playwright)
        except Exception as e:
            pp.set_test_error({'msg': str(e)})
        try:
            await pp.task
        except asyncio.CancelledError:
            pass
        return pp

    def test_simple_web_face(self):
        pp = asyncio.run(self.simple_web_face())
        for res in pp.test_errors:
            with self.subTest(value=res.get('msg')):
                self.assertTrue(False, res.get('msg'))


async def run(playwright) -> None:
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    page.set_default_timeout(8000)
    await page.goto("http://localhost:9090/")
    await page.get_by_role("button", name="first.main.admin").click()
    await page.get_by_role("button", name="first.main.admin").click()
    await page.get_by_role("button", name="first.main.admin").click()
    await page.get_by_label("Команда").click()
    await page.get_by_label("Команда").fill("exit")
    await page.get_by_role("button", name="SEND").click()
    await context.close()
    await browser.close()

if __name__ == '__main__':
    unittest.main()
