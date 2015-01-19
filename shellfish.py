import types
import sys
import os
import os.path
import subprocess
import io


def stmnt_cls_fctry(name, module):
    """Creates a Command class of that name if a command in PATH
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

    """FIXME: add doc"""

    def __init__(self):
        self._stdin = None
        self._stdout = PIPE
        self._stdout_mode = 'w'
        self._stderr = PIPE
        self._stderr_mode = 'w'
        self._universal_newlines = True

    @property
    def universal_newlines(self):
        return self._universal_newlines

    def _get_stdin(self):
        """stdin of the statement"""
        return self._stdin

    def _set_stdin(self, value):
        """Stdin of the statement. Supported types for value are:
        * None -- no stdin redirection; default
        * PIPE -- creates a pipe to the standard stream
        * "filename" -- retrieve stdin from filename given as str
        * fh -- retrieve stdin from file handle
        * DEVNULL -- retrieve stdin from file object os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close file after execution
            self._stdin = open(value)
        else:
            self._stdin = value

    stdin = property(fget=lambda self: self._get_stdin(),
                     fset=lambda self, value: self._set_stdin(value))

    def _get_stdout(self):
        """stdout of the statement"""
        return self._stdout

    def _set_stdout(self, value):
        """Stdout of the statement. Supported types for value are:
        PIPE -- creates a pipe to the standard stream; default
        None -- no redirection
        "filename" -- write stdout to file 
        filehandle -- write stdout to a file handle
        DEVNULL -- redirect stdout to file handle os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close the file handle
            self._stdout = open(value, self.stdout_mode)
        else:
            self._stdout = value

    stdout = property(fget=lambda self: self._get_stdout(),
                      fset=lambda self, value: self._set_stdout(value))

    @property
    def stdout_mode(self):
        """write mode to stdout"""
        return self._stdout_mode

    @stdout.setter
    def stdout_mode(self, mode):
        self._stdout_mode = mode

    def _get_stderr(self):
        """stderr of the statement"""
        return self._stderr

    def _set_stderr(self, value):
        """Stderr of the statement. Supported types for value are:
        PIPE -- creates a pipe to the standard stream; default
        None -- no redirection
        "filename" -- write stderr to file 
        filehandle -- write stderr to a file handle
        DEVNULL -- redirect stderr to file handle os.devnull
        """
        if isinstance(value, str):
            # FIXME: think about how to close the file handle
            self._stderr = open(value, self.stderr_mode)
        else:
            self._stderr = value

    stderr = property(fget=lambda self: self._get_stderr(),
                      fset=lambda self, value: self._set_stderr(value))

    @property
    def stderr_mode(self):
        """write mode to stderr"""
        return self._stderr_mode

    @stderr.setter
    def stderr_mode(self, mode):
        self._stderr_mode = mode

    def __call__(self):
        """abstract method to execute the statement"""
        raise NotImplementedError()

    def __lt__(self, other):
        """Sets the stdin of the statement. Syntax:
        self < other
        """
        self.stdin = other
        return self

    def __gt__(self, other):
        """Sets the stdout of the statement. Syntax:
        self > other
        """
        self.stdout = other
        return self

    def __ge__(self, other):
        """Sets the stderr of the statement. Syntax:
        self >= other
        """
        self.stderr = other
        return self

    def __or__(self, other):
        """Pipes stdout of this statement to stdin of the other
        statement. Only Statement objects are supported. Syntax:
        self | other
        """
        return PipeStatement(self, other)


class Command(Statement):

    """FIXME: add doc"""

    def __init__(self, cmd, *args, **kwds):
        super().__init__()
        self._cmd = cmd
        self._arguments = args
        self._options = kwds
        self._subprocess = None

    @property
    def subprocess(self):
        return self._subprocess

    def _get_stmnt(self):
        """create a list of command arguments and options"""
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
        """Executes the command and returns the subprocess.Popen object"""
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
        """Maps our stdin values to a valid subprocess argument"""
        sp_stdin = None
        our_stdin = self.stdin
        sp_stdin = our_stdin
        return sp_stdin

    def _calc_sp_stdout(self):
        """Maps our stdout value to a valid subprocess argument"""
        sp_stdout = None
        our_stdout = self.stdout
        sp_stdout = our_stdout
        return sp_stdout

    def _calc_sp_stderr(self):
        """Maps our stderr value to a valid subprocess argument"""
        sp_stderr = None
        our_stderr = self.stderr
        sp_stderr = our_stderr
        return sp_stderr


class PipeStatement(Statement):

    """FIXME: add doc"""

    def __init__(self, left, right):
        super().__init__()
        self.left = left
        self.right = right

    def _get_stdin(self):
        return self.left.stdin

    def _set_stdin(self, value):
        self.left.stdin = value

    def _get_stdout(self):
        return self.right.stdout

    def _set_stdout(self, value):
        self.right.stdout = value

    def _get_stderr(self):
        return self.right.stderr

    def _set_stderr(self, value):
        self.right.stderr = value

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
        gst    -- Global symbol table of the module where the proxy
                  should be used.
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
