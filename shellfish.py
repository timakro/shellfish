import types
import sys
import os
import os.path
import subprocess
import io


def stmnt_cls_fctry(name, module):
    """Create a Statement class of that name if a command in PATH
    exists for that name.
    """
    try:
        paths = os.environ['PATH'].split(os.pathsep)
    except KeyError:
        paths = []

    for path in paths:
        cmd = os.path.join(path, name)
        if os.path.exists(cmd) and os.access(path, os.X_OK):
            def __init__(self, *args, **kwds):
                Command.__init__(self, cmd, *args, **kwds)

            cls = type(name, (Command,), {'__init__': __init__})
            setattr(module, name, cls)
            return cls

    return CommandNotFoundError()


class ShellfishError(Exception):
    pass


class CommandNotFoundError(ShellfishError):
    pass


PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
DEVNULL = subprocess.DEVNULL


class Statement():

    def __init__(self):
        self._stdin = self.default_stdin()
        self._stdout = self.default_stdout()
        self._stderr = self.default_stderr()
        self._retcode = None

    def default_stdin(self):
        return None

    def default_stdout(self):
        return PIPE

    def default_stderr(self):
        return PIPE

    @property
    def stdin(self):
        """stdin of the statement"""
        return self._stdin

    @stdin.setter
    def stdin(self, value):
        """Supported:
        * None -- no stdin redirection; default
        * "filename" -- retrieve stdin from filename given as str
        * fh -- retrieve stdin from file handle
        * DEVNULL -- retrieve stdin from file object os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close file after execution
            self._stdin = open(value)
        else:
            self._stdin = value

    @property
    def stdout(self):
        """stdout of the statement"""
        return self._stdout

    @stdout.setter
    def stdout(self, value, mode='w'):
        """Supported:
        None -- no redirection; default
        "filename" -- write stdout to file 
        filehandle -- write stdout to a file handle
        DEVNULL -- redirect stdout to file handle os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close the file handle
            self._stdout = open(value, mode)
        else:
            self._stdout = value

    @property
    def stderr(self):
        """stderr of the statement"""
        return self._stderr

    @stderr.setter
    def stderr(self, value, mode='w'):
        """Supported:
        None -- no redirection; default
        "filename" -- write stderr to file 
        filehandle -- write stderr to a file handle
        DEVNULL -- redirect stderr to file handle os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close the file handle
            self._stderr = open(value, mode)
        else:
            self._stderr = value

    @property
    def retcode(self):
        """return code of the statement execution"""
        return self._retcode

    @retcode.setter
    def retcode(self, value):
        self._retcode = value

    def __call__(self, *args, **kwds):
        """Abstract method to execute the statement"""
        raise NotImplementedError()

    def __lt__(self, other):
        """Syntax:
        self < other
        """
        self.stdin = other
        return self

    def __gt__(self, other):
        """Syntax:
        self > other
        """
        self.stdout = other
        return self

    def __ge__(self, other):
        """Syntax:
        self >= other
        """
        self.stderr = other
        return self

    def __or__(self, other):
        """Only Statement objects are supported
        Syntax:
        self | other
        """
        return PipeStatement(self, other)

    def __call__(self):
        """abstract method"""
        raise NotImplementedError()


class Command(Statement):

    def __init__(self, cmd, *args, **kwds):
        super().__init__()
        self._cmd = cmd
        self._arguments = args
        self._options = kwds
        self._universal_newlines = self.default_universal_newlines()
        self._subprocess = None

    def default_universal_newlines(self):
        return True

    @property
    def universal_newlines(self):
        return self._universal_newlines

    @property
    def subprocess(self):
        return self._subprocess

    def _get_stmnt(self):
        stmnt = [self._cmd, ]
        stmnt.extend(self._arguments)
        for k, v in self._options.items():
            if len(k) > 1:
                stmnt.append('--' + k)
            else:
                stmnt.append('-' + k)
            stmnt.append(v)
        return stmnt

    def __call__(self):
        """Executes the command and returns the subprocessi.Popen object"""
        stmnt = self._get_stmnt()
        sp_stdin = self._calc_sp_stdin()
        sp_stdout = self._calc_sp_stdout()
        sp_stderr = self._calc_sp_stderr()
        p = subprocess.Popen(
            stmnt, stdin=sp_stdin, stdout=sp_stdout, stderr=sp_stderr,
            universal_newlines=self.universal_newlines)
        self._subprocess = p
        return p

    def _calc_sp_stdin(self):
        """Maps our stdin values to valid subprocess argument"""
        sp_stdin = None
        our_stdin = self.stdin
        sp_stdin = our_stdin
        return sp_stdin

    def _calc_sp_stdout(self):
        """Maps our stdout value to valid subprocess argument"""
        sp_stdout = None
        our_stdout = self.stdout
        sp_stdout = our_stdout
        return sp_stdout

    def _calc_sp_stderr(self):
        """Maps our stderr value to valid subprocess argument"""
        sp_stderr = None
        our_stderr = self.stderr
        sp_stderr = our_stderr
        return sp_stderr


class PipeStatement(Statement):

    def __init__(self, left, right):
        super().__init__()
        self.left = left
        self.right = right

    @Statement.stdin.setter
    def stdin(self, value):
        self.left.stdin = value

    def __call__(self):
        left = self.left
        right = self.right

        left.stdout = PIPE
        lp = left()
        right.stdin = lp.stdout
        return right()


class ModuleProxy(types.ModuleType):

    """ModuleProxy is a proxy for the module, which is used
    for importing the shellfish module. It will create and
    return a Cmd class for the requested name.
    """

    def __init__(self, module, gst):
        """Arguments:
        module -- The module to be proxied.
        gst    -- Global symbol table of the module where the proxy should be used.
        """
        super().__init__(module.__name__, doc=module.__doc__)

        self._module = module
        self._gst = gst

    def __getattr__(self, name):
        """Called when name isn't inthe global symbol table or module
        dictionary. It will create a class with that name inhiring from
        shellfish.Cmd.
        """
        # FIXME: support star imports
        if name == '__all__':
            raise ImportError("importing * isn't supported")

        # check if the proxied module has an attribute with this name
        try:
            return getattr(self._module, name)
        except AttributeError:
            pass

        # try:
        #    return self.__dict__[name]
        # except KeyError:
        #    pass

        return stmnt_cls_fctry(name, self._module)

    def __call__(self, stmnt):
        """executes a statement"""
        process = stmnt()
        stdout, stderr = process.communicate()
        retcode = process.wait()
        self.retcode = retcode
        return retcode, stdout, stderr

if not __name__ == '__main__':
    # set proxy object in front of this module
    module = sys.modules[__name__]
    gst = globals()
    sys.modules[__name__] = ModuleProxy(module, gst)
