import gunicorn.app.base


class Server(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = dict(options or {})
        self.application = app
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if value is None:
                continue
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application
