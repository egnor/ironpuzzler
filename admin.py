# Iron Puzzler administrative interface handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

class AdminPage(webapp.RequestHandler):
  def get(self):
    game = model.Game.get(model.GAME_KEY) or model.Game(key=model.GAME_KEY)
    values = dict([(p, getattr(game, p)) for p in game.properties()])
    self.response.out.write(template.render("admin.dj.html", values))

  def post(self):
    game = model.Game.get(model.GAME_KEY) or model.Game(key=model.GAME_KEY)
    game.ingredients = [self.request.get("ingredient%d" % i) for i in range(3)]
    game.ingredients = [i for i in game.ingredients if i]
    game.ingredients_visible = bool(self.request.get("ingredients_visible"))
    game.put()
    self.redirect("/admin")

app = webapp.WSGIApplication([('/admin', AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
