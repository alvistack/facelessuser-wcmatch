"""Handle path matching."""
import re
import os
import stat
import copyreg
from . import util

# `O_DIRECTORY` may not always be defined
DIR_FLAGS = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
# Right half can return an empty set if not supported
SUPPORT_DIR_FD = {os.open, os.stat} <= os.supports_dir_fd and os.scandir in os.supports_fd


RE_WIN_MOUNT = (
    re.compile(r'\\|[a-z]:(?:\\|$)', re.I),
    re.compile(br'\\|[a-z]:(?:\\|$)', re.I)
)
RE_MOUNT = (
    re.compile(r'/'),
    re.compile(br'/')
)


class _Match:
    """Match the given pattern."""

    def __init__(self, filename, include, exclude, real, path, follow):
        """Initialize."""

        self.filename = filename
        self.include = include
        self.exclude = exclude
        self.real = real
        self.path = path
        self.follow = follow
        self.is_bytes = isinstance(self.filename, bytes)
        self.ptype = util.BYTES if self.is_bytes else util.UNICODE

    def _fs_match(self, pattern, filename, is_dir, sep, follow, symlinks, root, dir_fd):
        """
        Match path against the pattern.

        Since `globstar` doesn't match symlinks (unless `FOLLOW` is enabled), we must look for symlinks.
        If we identify a symlink in a `globstar` match, we know this result should not actually match.

        We only check for the symlink if we know we are looking at a directory.
        And we only call `lstat` if we can't find it in the cache.

        We know it's a directory if:

        1. If the base is a directory, all parts are directories.
        2. If we are not the last part of the `globstar`, the part is a directory.
        3. If the base is a file, but the part is not at the end, it is a directory.

        """

        matched = False

        end = len(filename)
        base = None
        m = pattern.fullmatch(filename)
        if m:
            matched = True
            # Lets look at the captured `globstar` groups and see if that part of the path
            # contains symlinks.
            if not follow:
                last = len(m.groups())
                try:
                    for i, star in enumerate(m.groups(), 1):
                        if star:
                            at_end = m.end(i) == end
                            parts = star.strip(sep).split(sep)
                            if base is None:
                                base = os.path.join(root, filename[:m.start(i)])
                            for part in parts:
                                base = os.path.join(base, part)
                                key = (dir_fd, base)
                                if is_dir or i != last or not at_end:
                                    is_link = symlinks.get(key, None)
                                    if is_link is None:
                                        if dir_fd is None:
                                            is_link = os.path.islink(base)
                                            symlinks[key] = is_link
                                        else:
                                            try:
                                                st = os.lstat(base, dir_fd=dir_fd)
                                            except (OSError, ValueError):  # pragma: no cover
                                                is_link = False
                                            else:
                                                is_link = stat.S_ISLNK(st.st_mode)
                                            symlinks[key] = is_link
                                    matched = not is_link
                                    if not matched:
                                        break
                        if not matched:
                            break
                except OSError:  # pragma: no cover
                    matched = False
        return matched

    def _match_real(self, symlinks, root, dir_fd):
        """Match real filename includes and excludes."""

        sep = '\\' if util.platform() == "windows" else '/'
        if isinstance(self.filename, bytes):
            sep = os.fsencode(sep)

        is_dir = self.filename.endswith(sep)
        try:
            if dir_fd is None:
                is_file_dir = os.path.isdir(os.path.join(root, self.filename))
            else:
                try:
                    st = os.stat(os.path.join(root, self.filename), dir_fd=dir_fd)
                except (OSError, ValueError):  # pragma: no cover
                    is_file_dir = False
                else:
                    is_file_dir = stat.S_ISDIR(st.st_mode)
        except OSError:  # pragma: no cover
            return False

        if not is_dir and is_file_dir:
            is_dir = True
            filename = self.filename + sep
        else:
            filename = self.filename

        matched = False
        for pattern in self.include:
            if self._fs_match(pattern, filename, is_dir, sep, self.follow, symlinks, root, dir_fd):
                matched = True
                break

        if matched:
            if self.exclude:
                for pattern in self.exclude:
                    if self._fs_match(pattern, filename, is_dir, sep, True, symlinks, root, dir_fd):
                        matched = False
                        break

        return matched

    def match(self, root_dir=None, dir_fd=None):
        """Match."""

        if self.real:
            root = root_dir if root_dir else (b'.' if self.is_bytes else '.')

            if dir_fd is not None and not SUPPORT_DIR_FD:
                dir_fd = None

            if not isinstance(self.filename, type(root)):
                raise TypeError(
                    "The filename and root directory should be of the same type, not {} and {}".format(
                        type(self.filename), type(root_dir)
                    )
                )

            if self.include and not isinstance(self.include[0].pattern, type(self.filename)):
                raise TypeError(
                    "The filename and pattern should be of the same type, not {} and {}".format(
                        type(self.filename), type(self.include[0].pattern)
                    )
                )

            is_abs = (
                RE_WIN_MOUNT if util.platform() == "windows" else RE_MOUNT
            )[self.ptype].match(self.filename) is not None

            if is_abs:
                exists = os.path.lexists(self.filename)
            elif dir_fd is None:
                exists = os.path.lexists(os.path.join(root, self.filename))
            else:
                try:
                    os.lstat(os.path.join(root, self.filename), dir_fd=dir_fd)
                except (OSError, ValueError):  # pragma: no cover
                    exists = False
                else:
                    exists = True

            if exists:
                symlinks = {}
                return self._match_real(symlinks, root, dir_fd)
            else:
                return False

        matched = False
        for pattern in self.include:
            if pattern.fullmatch(self.filename):
                matched = True
                break

        if matched:
            matched = True
            if self.exclude:
                for pattern in self.exclude:
                    if pattern.fullmatch(self.filename):
                        matched = False
                        break
        return matched


class WcRegexp(util.Immutable):
    """File name match object."""

    __slots__ = ("_include", "_exclude", "_real", "_path", "_follow", "_hash")

    def __init__(self, include, exclude=None, real=False, path=False, follow=False):
        """Initialization."""

        super(WcRegexp, self).__init__(
            _include=include,
            _exclude=exclude,
            _real=real,
            _path=path,
            _follow=follow,
            _hash=hash(
                (
                    type(self),
                    type(include), include,
                    type(exclude), exclude,
                    type(real), real,
                    type(path), path,
                    type(follow), follow
                )
            )
        )

    def __hash__(self):
        """Hash."""

        return self._hash

    def __len__(self):
        """Length."""

        return len(self._include) + (len(self._exclude) if self._exclude is not None else 0)

    def __eq__(self, other):
        """Equal."""

        return (
            isinstance(other, WcRegexp) and
            self._include == other._include and
            self._exclude == other._exclude and
            self._real == other._real and
            self._path == other._path and
            self._follow == other._follow
        )

    def __ne__(self, other):
        """Equal."""

        return (
            not isinstance(other, WcRegexp) or
            self._include != other._include or
            self._exclude != other._exclude or
            self._real != other._real or
            self._path != other._path or
            self._follow != other._follow
        )

    def match(self, filename, root_dir=None, dir_fd=None):
        """Match filename."""

        return _Match(
            filename,
            self._include,
            self._exclude,
            self._real,
            self._path,
            self._follow
        ).match(
            root_dir=root_dir,
            dir_fd=dir_fd
        )


def _pickle(p):
    return WcRegexp, (p._include, p._exclude, p._real, p._path, p._follow)


copyreg.pickle(WcRegexp, _pickle)
