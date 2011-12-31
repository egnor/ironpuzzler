# Iron Puzzler main page handler

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

class MainPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    props = { "game": model.GetProperties(game), "teams": [] }
    props_by_team = {}
    for team in model.Team.all().ancestor(game):
      team_props = props_by_team[team.key()] = model.GetProperties(team)
      team_props["solves"] = set()
      team_props["solve_time"] = 0
      props["teams"].append(team_props)

    for guess in model.Guess.all().ancestor(game).order("timestamp"):
      if guess.answer in guess.parent().answers:
        team_props = props_by_team[guess.team.key()]
        if guess.parent().key() not in team_props["solves"]:
          team_props["solves"].add(guess.parent().key())
          team_props["solve_time"] = guess.timestamp

    props["teams"].sort(key = lambda tp:
        (-len(tp["solves"]), tp["solve_time"], tp["name"]))

    self.response.out.write(template.render("main.dj.html", props))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
