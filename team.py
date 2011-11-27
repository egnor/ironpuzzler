# Iron Puzzler team page handler

import logging

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model
import login

FETCH = 1000


class TeamPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    props = {
      "error": dict([(e, 1) for e in self.request.get_all("error")]),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "team_puzzles": [],
      "all_puzzles": [],
    }

    for number, puzzle in enumerate(model.Puzzle.get(game.puzzle_order)):
      puzzle_props = model.GetProperties(puzzle)
      puzzle_props["number"] = number + 1
      puzzle_props["is_team"] = (puzzle.key().parent() == team.key())
      props["all_puzzles"].append(puzzle_props)

    for puzzle in model.Puzzle.all().ancestor(team).fetch(FETCH):
      puzzle_props = model.GetProperties(puzzle)
      puzzle_props["number"] = model.GetPuzzleNumber(game, puzzle)
      props["team_puzzles"].append(puzzle_props)

    self.response.out.write(template.render("team.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    self.redirect("/team?t=%d" % team.key().id())
    team.name = self.request.get("name") or team.name
    team.email = self.request.get("email")

    set_pw = self.request.get("set_password")
    confirm_pw = self.request.get("confirm_password")
    if set_pw or confirm_pw:
      if set_pw != confirm_pw:
        self.response.headers["location"] += "&error=set_password"
      else:
        team.password = set_pw

    team.put()


app = webapp.WSGIApplication([("/team", TeamPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
