## Pherguson
Proof of concept [Gopher Protocol](https://en.wikipedia.org/wiki/Gopher_(protocol)) client using [Urwid](http://urwid.org/) and [Ueberzug](https://github.com/seebye/ueberzug).

## Installation
```bash
git clone https://github.com/olivierpilotte/pherguson
cd pherguson
pip install --user -r requirements.txt
```

or using a virtual environment:
```bash
venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run
To run Pherguson:
```bash
python pherguson.py
```

or using the virtual environment:
```bash
.venv/bin/python pherguson.py
```

## User guide
### Url Bar
To focus the Url bar, use `tab` of `ctrl+l`. To leave the Url bar, press `Tab` or `Esc`.

### General navigation
Up: `k`, `up arrow`\
Down: `j`, `down arrow`

Page Up: `page up`, `K` (shift+k)\
Page Down: `page down`, `J` (shift+j)

Forward: `l`, `right arrow`, `enter`\
Back: `h`, `left arrow`, `backspace`

### Image preview
Images that can be showed inline (in the terminal) are indicated with a `+` sign.
Simply use the any Forward navigation keys to show the image.

To open the image in an external program (e.g. `feh`), press any of the Forward keys again.

To collapse the image, press any of the `Back` navigation keys or `Escape`.

## Todo:
* refactor the code (it's a mess)
* better handling of sockets
* browser cache (specifically for images)
* history overlay
* bookmarks
* proper "homepage" (offline)
