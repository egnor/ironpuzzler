# Iron Puzzler main page handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

class MainPage(webapp.RequestHandler):
  def get(self):
    game = model.Game.get(model.GAME_KEY)
    values = dict([(p, getattr(game, p)) for p in game.properties()])
    self.response.out.write(template.render("main.dj.html", values))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
