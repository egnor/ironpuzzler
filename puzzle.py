# Iron Puzzler puzzle page handler

from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import datetime
import login
import model
import re
import urllib

def MaybeGetPuzzle(ancestor, request):
  n = request.get("p")
  for p in model.Puzzle.all().ancestor(ancestor).filter("number", n): return p
  return None


SORTKEY_RE = re.compile("([^0-9-]*)([0-9-]*)")

def SortKey(puzzle):
  key = [(a, int(n or 0)) for a, n in SORTKEY_RE.findall(puzzle.number or "")]
  key.append(puzzle.key())
  return key


def NormalizeAnswer(answer):
  return re.sub('[\W]+', '', answer).upper()


def NormalizeScore(score):
  try: score = float(score)
  except: return 3.0
  return (score < 0.0 or score > 5.0) and 3.0 or score


class PuzzlePage(blobstore_handlers.BlobstoreUploadHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(team, self.request)
    if not puzzle: return self.error(404)
    if puzzle.parent_key() != team.key(): return self.error(403)

    props = {
      "form_url": blobstore.create_upload_url("/puzzle"),
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
      "comments": [],
      "votes": [],
      "solves": [],
    }

    no_scores = model.Feedback().scores
    for feedback in model.Feedback.all().ancestor(puzzle):
      comment = (feedback.comment or "").strip()
      if comment: props["comments"].append(comment)
      props["votes"].append(feedback.scores)

    props["puzzle"]["answers"] = "\n".join(props["puzzle"].get("answers", []))
    props["comments"].sort(key=unicode.lower)
    props["votes"].sort(reverse=True)

    solvers = {}
    for guess in model.Guess.all().ancestor(puzzle).order("timestamp"):
      if guess.answer in puzzle.answers and not solvers.get(guess.team.key()):
        solvers[guess.team.key()] = 1
        props["solves"].append(guess)

    self.response.out.write(template.render("puzzle.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)
    if puzzle.parent_key() != team.key(): return self.error(403)
    self.redirect("/team?t=%d" % team.key().id())

    updates = {}
    for arg in self.request.arguments():
      if arg.endswith(".orig"): continue
      orig_value = urllib.unquote(self.request.get(arg + ".orig", ""))
      new_value = self.request.get(arg).replace("\r\n", "\n")
      if new_value != orig_value: updates[arg] = new_value

    for blobinfo in self.get_uploads(field_name = "puzzle_file"): 
      if puzzle.puzzle_blob: blobstore.delete(puzzle.puzzle_blob.key())
      puzzle.puzzle_blob = blobinfo

    for blobinfo in self.get_uploads(field_name = "solution_file"):
      if puzzle.solution_blob: blobstore.delete(puzzle.solution_blob.key())
      puzzle.solution_blob = blobinfo

    if "title" in updates: puzzle.title = updates.get("title")

    if "answers" in updates:
      puzzle.answers = []
      for answer in updates.get("answers").split("\n"):
        answer = NormalizeAnswer(answer)
        if answer: puzzle.answers.append(answer)

    if "errata" in updates:
      puzzle.errata_timestamp = datetime.datetime.now()
      puzzle.errata = updates.get("errata")

    if "solution" in updates: puzzle.solution = updates.get("solution")

    puzzle.put()


app = webapp.WSGIApplication([("/puzzle", PuzzlePage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
