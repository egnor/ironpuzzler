# Iron Puzzler puzzle attachment download handler

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import blobstore
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import model
from puzzle import MaybeGetPuzzle


class DownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self):
    game = model.GetGame()
    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)

    # Access control:
    #   (Solving enabled AND type is "p") OR
    #   Voting enabled OR Results enabled OR
    #   Team is puzzle author OR Team solved puzzle
    file = self.request.get("f")
    if not (game.voting_enabled or game.results_enabled or
        (game.solving_enabled and file == "p")):
      team = login.GetTeamOrRedirect(game, self.request, self.response)
      if not team: return
      if puzzle.parent_key() != team.key():
        guesses = model.Guess.all().ancestor(puzzle).filter("team", team.key())
        if not [g for g in guesses if g in puzzle.answers]:
          return self.error(403)

    blobinfo = { "p": puzzle.puzzle_blob, "s": puzzle.solution_blob }.get(file)
    if not blobinfo: return self.error(404)
    self.send_blob(blobinfo, save_as="%s%s-%s" %
        (file, self.request.get("p"), blobinfo.filename or "file"))


app = webapp.WSGIApplication([("/download", DownloadHandler)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
