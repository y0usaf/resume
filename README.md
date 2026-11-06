# resume

My one-page résumé: [`index.html`](index.html) and [`resume.pdf`](resume.pdf).

Edit `resume.json`, run `python build.py` to fill `index.template.html` into `index.html`, then print the PDF and check it is one page:

```sh
chromium --headless --no-pdf-header-footer --virtual-time-budget=10000 --print-to-pdf=resume.pdf "file://$PWD/index.html"
```

`**double asterisks**` in `resume.json` set a phrase bold on a yellow highlight. `nix flake check` fails if `index.html` is out of date with `resume.json`.
