# Iron Puzzler puzzle page handler

import logging
import re
import urllib

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model
import login

FETCH = 1000


def MaybeGetPuzzle(team, request):
  p_name = request.get("p")
  return p_name and model.Puzzle.get_by_key_name(p_name, team)


class PuzzlePage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(team, self.request)
    if not puzzle: return self.error(404)

    props = {
      "error": dict([(e, 1) for e in self.request.get_all("error")]),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
    }

    props["puzzle"]["answers"] = "\n".join(props["puzzle"].get("answers", []))

    props["puzzle"]["number"] = model.GetPuzzleNumber(game, puzzle)

    self.response.out.write(template.render("puzzle.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(team, self.request)
    if not puzzle: return self.error(404)
    self.redirect("/puzzle?t=%d&p=%s" % (team.key().id(), puzzle.key().name()))

    updates = {}
    for arg in self.request.arguments():
      if arg.endswith("_orig"): continue
      orig_value = urllib.unquote(self.request.get(arg + "_orig", ""))
      new_value = self.request.get(arg)
      if new_value != orig_value: updates[arg] = new_value

    if "title" in updates: puzzle.title = updates.get("title")

    if "answers" in updates:
      puzzle.answers = []
      for answer in updates.get("answers").split("\n"):
        answer = re.sub('[\W]+', '', answer).upper()
        if answer: puzzle.answers.append(answer)

    if "errata" in updates: puzzle.errata = updates.get("errata")

    if "solution" in updates: puzzle.errata = updates.get("solution")

    puzzle.put()


app = webapp.WSGIApplication([("/puzzle", PuzzlePage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
