class Stub:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        print(msg)
