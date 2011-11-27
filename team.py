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

    puzzle_props = {}
    for number, puzzle in enumerate(model.Puzzle.get(game.puzzle_order)):
      pp = puzzle_props[puzzle.key()] = model.GetProperties(puzzle)
      pp["number"] = number + 1
      pp["is_team"] = (puzzle.key().parent() == team.key())
      pp["guess_count"] = 0
      pp["answer_set"] = set(puzzle.answers)
      props["all_puzzles"].append(pp)

    query = model.Guess.all().ancestor(game)
    for guess in query.filter("team", team.key()):
      pp = puzzle_props.get(guess.parent().key())
      if pp:
        if guess.answer in pp["answer_set"]: pp["solve_time"] = guess.timestamp
        pp["guess_count"] += 1

    for puzzle in model.Puzzle.all().ancestor(team):
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
