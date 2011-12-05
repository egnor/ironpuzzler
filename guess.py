# Iron Puzzler submission page handler

import logging
import re

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import model


def NormalizeAnswer(answer):
  return re.sub('[\W]+', '', answer).upper()


def MaybeGetPuzzle(game, request):
  try: p_key = game.puzzle_order[int(request.get("n")) - 1]
  except Exception: return None
  return model.Puzzle.get(p_key)


class GuessPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    if not game.solving_enabled: return self.error(403)

    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    props = {
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
      "guesses": [],
    }

    query = model.Guess.all().ancestor(puzzle)
    for guess in query.filter("team", team.key()).order("-timestamp"):
      guess_props = model.GetProperties(guess)
      if guess.answer in puzzle.answers:
        guess_props["is_correct"] = True
        props.setdefault("solve_time", guess.timestamp)
      props["guesses"].append(guess_props)

    props["puzzle"]["number"] = int(self.request.get("n"))

    self.response.out.write(template.render("guess.dj.html", props))


  def post(self):
    game = model.GetGame()
    if not game.solving_enabled: return self.error(403)

    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)
    self.redirect("/guess?t=%d&n=%s" % (team.key().id(), self.request.get("n")))

    answer = NormalizeAnswer(self.request.get("answer", ""))
    if answer: model.Guess(parent=puzzle, answer=answer, team=team).put()


app = webapp.WSGIApplication([("/guess", GuessPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
