class Environment(object):
    """ used to simulate a browser environment"""
    def __init__(self, width, height, device=None, user_agent=None):
        """ width and height are the dimensions of the screen"""
        self.width = width
        self.height = height
        self.device = device
        self.user_agent = user_agent