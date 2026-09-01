SSS v3.1.1 — GitHub Pages Feed Hotfix
=======================================

The release-feed builder expects the final HTTPS location where latest.json
and the .sssupdate package will be downloaded.

A Git clone URL such as:

  https://github.com/VicelikeElm/Sunday-Service-System.git

is not itself that static download folder.

v3.1.1 lets you paste the GitHub repository URL anyway and derives:

  https://VicelikeElm.github.io/Sunday-Service-System/stable

when Channel is:

  stable

The public feed becomes:

  https://VicelikeElm.github.io/Sunday-Service-System/stable/latest.json

Recommended repository layout:

  docs/
    .nojekyll
    index.html
    stable/
      latest.json
      latest.json.p7s
      SundayServiceSystem-Update-vX.Y.Z.sssupdate

GitHub Pages:
  Settings -> Pages
  Source: Deploy from a branch
  Branch: main
  Folder: /docs

New helper:
  Stage-SSS-GitHub-Pages-Feed.bat

It copies the generated signed feed into docs\stable or docs\beta inside
your local cloned repository. It does NOT commit or push anything.

Correct builder inputs for your repository:

  GitHub repository URL:
    https://github.com/VicelikeElm/Sunday-Service-System.git

  Channel:
    stable

Do not paste the repository URL into the Channel prompt.
