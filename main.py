# Iron Puzzler main page handler

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

class MainPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    props = { "game": model.GetProperties(game), "teams": [] }
    for team in model.Team.all().ancestor(game).order("name"):
      props["teams"].append(model.GetProperties(team))
    self.response.out.write(template.render("main.dj.html", props))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
