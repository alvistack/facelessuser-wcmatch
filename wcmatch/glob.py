"""
Wild Card Match.

A custom implementation of glob.

Licensed under MIT
Copyright (c) 2018 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
import os
import sys
from . import _wcparse
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWCHARS", "DOTGLOB",
    "NOEXTGLOB", "NOGLOBSTAR", "NEGATE", "MINUSNEGATE", "NOBRACE",
    "F", "I", "R", "D", "E", "G", "N", "M",
    "iglob", "glob", "globsplit", "globmatch", "globfilter", "escape"
)

# We don't use util.platform only because we mock it in tests,
# and scandir will not work with bytes on the wrong system.
WIN = sys.platform.startswith('win')
NO_SCANDIR_WORKAROUND = util.PY36 or (util.PY35 and not WIN)

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
D = DOTGLOB = _wcparse.DOTGLOB
E = NOEXTGLOB = _wcparse.EXTGLOB
G = NOGLOBSTAR = _wcparse.GLOBSTAR
N = NEGATE = _wcparse.NEGATE
M = MINUSNEGATE = _wcparse.MINUSNEGATE
B = NOBRACE = _wcparse.BRACE

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    DOTGLOB |      # Inverse
    NOEXTGLOB |    # Inverse
    NOGLOBSTAR |   # Inverse
    NEGATE |
    MINUSNEGATE |
    NOBRACE        # Inverse
)


def _flag_transform(flags):
    """Transform flags to glob defaults."""

    # Here we force PATHNAME and disable negation NEGATE
    flags = (flags & FLAG_MASK) | _wcparse.PATHNAME
    # Enable by default (flipped logic for fnmatch which disables it by default)
    flags ^= NOGLOBSTAR
    flags ^= NOBRACE
    flags ^= NOEXTGLOB
    return flags


class Glob(object):
    """Glob patterns."""

    def __init__(self, pattern, flags=0):
        """Init the directory walker object."""

        self.flags = _flag_transform(flags)
        self.dot = bool(self.flags & DOTGLOB)
        self.negate = bool(self.flags & NEGATE)
        self.globstar = bool(self.flags & _wcparse.GLOBSTAR)
        self.braces = bool(self.flags & _wcparse.BRACE)
        self.case_sensitive = _wcparse.get_case(self.flags) and not util.platform() == "windows"
        self.is_bytes = isinstance(pattern, bytes)
        self._parse_patterns(pattern)
        if util.platform() == "windows":
            self.sep = (b'\\', '\\')
        else:
            self.sep = (b'/', '/')

    def _parse_patterns(self, pattern):
        """Parse patterns."""

        self.pattern = []
        self.npattern = []
        for p in pattern:
            if _wcparse.is_negative(p, self.flags):
                self.pattern.extend(
                    _wcparse.compile(_wcparse.expand_braces(p, self.flags), self.flags)
                )
            else:
                self.pattern.extend(
                    _wcparse.WcPathSplit(x, self.flags).split() for x in _wcparse.expand_braces(p, self.flags)
                )

    def _is_globstar(self, name):
        """Check if name is a rescursive globstar."""

        return self.globstar and name in (b'**', '**')

    def _is_hidden(self, name):
        """Check if is file hidden."""

        return not self.dot and name[0:1] in (b'.', '.')

    def _is_this(self, name):
        """Check if "this" directory `.`."""

        return name in (b'.', '.') or name in self.sep

    def _is_parent(self, name):
        """Check if `..`."""

        return name in (b'..', '..')

    def _is_excluded(self, path):
        """Check if file is excluded."""

        excluded = False
        for n in self.npattern:
            excluded = not n.match(path)
            if excluded:
                break
        return excluded

    def _literal_match(self, name):
        """Do a simple match."""

        if not self.case_sensitive:
            return name.lower() == self._match
        else:
            return name == self._match

    def _set_match(self, match):
        """Set the match."""

        if isinstance(match, (str, bytes)):
            # Plain text match
            if not self.case_sensitive:
                self._match = match.lower()
            else:
                self._match = match
            self._matcher = self._literal_match
        else:
            # File match pattern
            self._matcher = match.match

    def _glob_shallow(self, curdir, dir_only=False):
        """Non recursive directory glob."""

        scandir = '.' if not curdir else curdir

        # Python will never return . or .., so fake it.
        if os.path.isdir(scandir):
            for special in ('.', '..'):
                if self._matcher(special):
                    yield os.path.join(curdir, special)

        try:
            if NO_SCANDIR_WORKAROUND:
                # Our current directory can be empty if the path starts with magic,
                # But we don't want to return paths with '.', so just use it to list
                # files, but use '' when constructing the path.
                with os.scandir(scandir) as scan:
                    for f in scan:
                        try:
                            if (not dir_only or f.is_dir()) and self._matcher(f.name):
                                yield os.path.join(curdir, f.name)
                        except OSError:
                            pass
            else:
                for f in os.listdir(scandir):
                    is_dir = os.path.isdir(os.path.join(curdir, f))
                    if (not dir_only or is_dir) and self._matcher(f):
                        yield os.path.join(curdir, f)
        except OSError:
            pass

    def _glob_deep(self, curdir, dir_only=False):
        """Recursive directory glob."""

        scandir = '.' if not curdir else curdir

        try:
            if NO_SCANDIR_WORKAROUND:
                # Our current directory can be empty if the path starts with magic,
                # But we don't want to return paths with '.', so just use it to list
                # files, but use '' when constructing the path.
                with os.scandir(scandir) as scan:
                    for f in scan:
                        try:
                            # Quicker to just test this way than to run through fnmatch.
                            if self._is_hidden(f.name):
                                continue
                            path = os.path.join(curdir, f.name)
                            if not dir_only or f.is_dir():
                                yield path
                            if f.is_dir():
                                yield from self._glob_deep(path, dir_only)
                        except OSError:
                            pass
            else:
                for f in os.listdir(scandir):
                    # Quicker to just test this way than to run through fnmatch.
                    if self._is_hidden(f):
                        continue
                    path = os.path.join(curdir, f)
                    is_dir = os.path.isdir(path)
                    if not dir_only or is_dir:
                        yield path
                    if is_dir:
                        yield from self._glob_deep(path, dir_only)
        except OSError:
            pass

    def _glob(self, curdir, this, rest):
        """
        Handle glob flow.

        There are really only a couple of cases:

        - File name.
        - File name pattern (magic).
        - Directory.
        - Directory name pattern (magic).
        - Extra slashes ////.
        - Lastyl globstar `**`.
        """

        is_magic = this.is_magic
        dir_only = this.dir_only
        target = this.pattern
        is_globstar = this.is_globstar

        # File (arrives via a _glob_deep)
        # We don't normally feed files through here,
        # but glob_deep sends evereything through here
        # if a next target is available.
        if not os.path.isdir(curdir) and os.path.lexists(curdir):
            self._set_match(target)
            if self._matcher(curdir):
                yield curdir

        # Directories
        elif is_magic and is_globstar:
            this = rest.pop(0) if rest else None

            # Throw away multiple consecutive globstars
            done = False
            while this and not done:
                if this:
                    dir_only = this.dir_only
                if this and this.is_globstar:
                    this = rest.pop(0) if rest else None
                else:
                    done = True

            # Glob star directory pattern `**`.
            for path in self._glob_deep(curdir, dir_only):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path

        elif not dir_only:
            # Files
            self._set_match(target)
            yield from self._glob_shallow(curdir)

        else:
            this = rest.pop(0) if rest else None

            # Normal directory
            self._set_match(target)
            for path in self._glob_shallow(curdir, True):
                if this:
                    yield from self._glob(path, this, rest[:])
                else:
                    yield path

    def _get_starting_paths(self, curdir):
        """
        Get the starting location.

        For case sensitive paths, we have to "glob" for
        it first as Python doesn't like for its users to
        think about case. By scanning for it, we can get
        the actual casing and then compare.
        """

        results = [curdir]

        if not self._is_parent(curdir) and not self._is_this(curdir):
            fullpath = os.path.abspath(curdir)
            basename = os.path.basename(fullpath)
            dirname = os.path.dirname(fullpath)
            if basename:
                self._set_match(basename)
                results = [os.path.basename(name) for name in self._glob_shallow(dirname, self)]

        return results

    def glob(self):
        """Starts off the glob iterator."""

        if self.is_bytes:
            curdir = bytes(os.curdir, 'ASCII')
        else:
            curdir = os.curdir

        for pattern in self.pattern:
            if pattern:
                if not pattern[0].is_magic:
                    # Path starts with normal plain text
                    # Lets verify the case of the starting directory (if possible)
                    this = pattern[0]

                    curdir = this[0]

                    if not os.path.isdir(curdir) and not os.path.lexists(curdir):
                        return

                    # Make sure case matches, but running case insensitive
                    # on a case sensitive file system may return more than
                    # one starting location.
                    results = self._get_starting_paths(curdir)
                    if not results:
                        # Nothing to do.
                        return

                    if this.dir_only:
                        # Glob these directories if they exists
                        for start in results:
                            if os.path.isdir(start):
                                rest = pattern[1:]
                                if rest:
                                    this = rest.pop(0)
                                    for match in self._glob(curdir, this, rest):
                                        if not self._is_excluded(match):
                                            yield match
                                elif not self._is_excluded(curdir):
                                    yield curdir
                    else:
                        # Return the file(s) and finish.
                        for start in results:
                            if os.path.lexists(start) and not self._is_excluded(start):
                                yield start
                else:
                    # Path starts with a magic pattern, let's get globbing
                    rest = pattern[:]
                    this = rest.pop(0)
                    for match in self._glob(curdir if not curdir == '.' else '', this, rest):
                        if not self._is_excluded(match):
                            yield match


def iglob(patterns, *, flags=0):
    """Glob."""

    yield from Glob(util.to_tuple(patterns), flags).glob()


def glob(patterns, *, flags=0):
    """Glob."""

    return list(iglob(util.to_tuple(patterns), flags=flags))


def globsplit(pattern, *, flags=0):
    """Split pattern by '|'."""

    return _wcparse.WcSplit(pattern, _flag_transform(flags)).split()


def translate(patterns, *, flags=0):
    """Translate glob pattern."""

    return _wcparse.translate(patterns, _flag_transform(flags))


def globmatch(filename, patterns, *, flags=0):
    """
    Check if filename matches pattern.

    By default case sensitivity is determined by the filesystem,
    but if `case_sensitive` is set, respect that instead.
    """

    flags = _flag_transform(flags)
    if not _wcparse.is_unix_style(flags):
        filename = util.norm_slash(filename)
    return _wcparse.compile(patterns, flags).match(filename)


def globfilter(filenames, patterns, *, flags=0):
    """Filter names using pattern."""

    matches = []

    flags = _flag_transform(flags)
    unix = _wcparse.is_unix_style(flags)
    obj = _wcparse.compile(patterns, flags)

    for filename in filenames:
        if not unix:
            filename = util.norm_slash(filename)
        if obj.match(filename):
            matches.append(filename)
    return matches


def escape(pattern):
    """Escape."""

    is_bytes = isinstance(pattern, bytes)
    replace = br'\\\1' if is_bytes else r'\\\1'
    magic = _wcparse.RE_BMAGIC if is_bytes else _wcparse.RE_MAGIC

    # Handle windows drives special.
    # Windows drives are handled special internally.
    # So we shouldn't escape them as we'll just have to
    # detect and undo it later.
    drive = b'' if is_bytes else ''
    if util.platform() == "windows":
        m = _wcparse.RE_WIN_PATH.match(pattern)
        if m:
            drive = m.group(0)
    pattern = pattern[len(drive):]

    return drive + magic.sub(replace, pattern)
