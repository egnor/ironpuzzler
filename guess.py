# Iron Puzzler submission page handler

import logging
import re

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import model
from puzzle import MaybeGetPuzzle, NormalizeAnswer, NormalizeScore


class GuessPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    feedback = model.Feedback.get_or_insert(str(team.key()), parent=puzzle)

    props = {
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
      "feedback": model.GetProperties(feedback),
      "guesses": [],
      "solve_teams": set(),
    }

    for guess in model.Guess.all().ancestor(puzzle).order("-timestamp"):
      if guess.answer in puzzle.answers:
        props["solve_teams"].add(guess.team.key())
      if guess.team.key() == team.key():
        props["guesses"].append(model.GetProperties(guess))
        if guess.answer in puzzle.answers:
          props["guesses"][-1]["is_correct"] = True
          props.setdefault("solve_time", guess.timestamp)

    props["puzzle"]["number"] = int(self.request.get("p"))

    self.response.out.write(template.render("guess.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    if game.solving_enabled:
      answer = NormalizeAnswer(self.request.get("answer", ""))
      if answer: model.Guess(parent=puzzle, answer=answer, team=team).put()

    self.redirect("/guess?t=%d&p=%s" % (team.key().id(), self.request.get("p")))

    if self.request.get("comment", None) is not None:
      feedback = model.Feedback(parent=puzzle, key_name=str(team.key()))
      feedback.comment = self.request.get("comment")
      if game.solving_enabled or game.voting_enabled:
        for s in range(len(feedback.scores)):
          feedback.scores[s] = NormalizeScore(self.request.get("score.%d" % s))

      feedback.put()
      self.redirect("/team?t=%d" % team.key().id())


app = webapp.WSGIApplication([("/guess", GuessPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
