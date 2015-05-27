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


class CalledProcessError(subprocess.CalledProcessError):
    pass


PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
DEVNULL = os.devnull


class Statement(object):

    """FIXME: add doc"""

    def __init__(self, universal_newlines=False):
        self._stdin = {
            'value': None,
            'heredoc': False
        }
        self._stdout = {
            'value': PIPE,
            'mode': 'w'
        }
        self._stderr = {
            'value': PIPE,
            'mode': 'w'
        }
        self._universal_newlines = universal_newlines

    def _get_universal_newlines(self):
        return self._universal_newlines

    def _set_universal_newlines(self, value):
        self._universal_newlines = bool(value)

    universal_newlines = property(
        fget=lambda self: self._get_universal_newlines())

    def _get_stdin(self):
        """stdin of the statement"""
        return self._stdin['value']

    def _set_stdin(self, value, heredoc=False):
        """Stdin of the statement. Supported types for value are:
        * None -- no stdin redirection; default
        * PIPE -- creates a pipe to the standard stream
        * fh -- retrieve stdin from file handle
        * DEVNULL -- retrieve stdin from file object os.devnull
        * "filename" -- retrieve stdin from filename given as str
        If heredoc is True, then value is not identified as file name,
        but the value is used as input.
        """
        self._stdin['heredoc'] = heredoc
        if not heredoc and isinstance(value, str):
            # FIXME: think about how to close file after execution
            self._stdin['value'] = open(value)
        else:
            self._stdin['value'] = value

    stdin = property(fget=lambda self: self._get_stdin(),
                     fset=lambda self, value: self._set_stdin(value))

    def _get_stdout(self):
        """stdout of the statement"""
        return self._stdout['value']

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
            self._stdout['value'] = open(value, self.stdout_mode)
        else:
            self._stdout['value'] = value

    stdout = property(fget=lambda self: self._get_stdout(),
                      fset=lambda self, value: self._set_stdout(value))

    @property
    def stdout_mode(self):
        """write mode to stdout"""
        return self._stdout['mode']

    @stdout_mode.setter
    def stdout_mode(self, mode):
        self._stdout['mode'] = mode

    def _get_stderr(self):
        """stderr of the statement"""
        return self._stderr['value']

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
            self._stderr['value'] = open(value, self.stderr_mode)
        else:
            self._stderr['value'] = value

    stderr = property(fget=lambda self: self._get_stderr(),
                      fset=lambda self, value: self._set_stderr(value))

    @property
    def stderr_mode(self):
        """write mode to stderr"""
        return self._stderr['mode']

    @stderr_mode.setter
    def stderr_mode(self, mode):
        self._stderr['mode'] = mode

    def __call__(self):
        """abstract method to execute the statement"""
        raise NotImplementedError()

    def __lt__(self, other):
        """Sets the stdin of the statement. Syntax:
        self < other
        """
        self.stdin = other
        return self

    def __le__(self, other):
        """Uses given string or bytes as stdin of the statement. Syntax:
        self <= other
        """
        self._set_stdin(other, True)
        self._set_universal_newlines(isinstance(other, str))
        return self

    def __gt__(self, other):
        """Sets the stdout or stdout and stderr of the statement. Syntax:
        self > stdout
        self > (stdout, stderr)
        """
        if isinstance(other, (tuple, list)):
            count = len(other)
            if count >= 1:
                self.stdout = other[0]
            if count >= 2:
                self.stderr = other[1]
        else:
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
        super(Command, self).__init__()
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
        if self._stdin['heredoc']:
            stdin = PIPE
        else:
            stdin = self.stdin
        return stdin

    def _calc_sp_stdout(self):
        """Maps our stdout value to a valid subprocess argument"""
        # actually nothing to do
        return self.stdout

    def _calc_sp_stderr(self):
        """Maps our stderr value to a valid subprocess argument"""
        # actually nothing to do
        return self.stderr

    def __repr__(self):
        return ' '.join(self._get_stmnt())


class PipeStatement(Statement):

    """FIXME: add doc"""

    def __init__(self, left, right):
        super(PipeStatement, self).__init__()
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
        self.left.stderr = value
        self.right.stderr = value

    def __call__(self):
        left = self.left
        right = self.right

        left.stdout = PIPE
        lp = left()
        right.stdin = lp.stdout
        return right()

    def __repr__(self):
        return '{} | {}'.format(repr(self.left), repr(self.right))


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
        super(ModuleProxy, self).__init__(module.__name__, doc=module.__doc__)

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

        return stmnt_cls_fctry(name, self._module)

    def __call__(self, stmnt):
        """executes a statement"""
        process = stmnt()
        if stmnt._stdin['heredoc']:
            stdin = stmnt.stdin
        else:
            stdin = None
        stdout, stderr = process.communicate(input=stdin)
        retcode = process.wait()
        self.retcode = retcode
        return retcode, stdout, stderr

    def call(self, stmnt):
        """Run the statement described by stmnt. Wait for command to complete,
        then return the retcode attribute.
        """
        retcode, _, _ = self(stmnt)
        return retcode

    def check_call(self, stmnt):
        """Run the statement described by stmnt. Wait for command to complete.
        If the return code was zero then return, otherwise raise
        CalledProcessError. The CalledProcessError object will have the return
        code in the returncode attribute.
        """
        retcode = self.call(stmnt)
        if retcode != 0:
            raise CalledProcessError(retcode, repr(stmnt))
        return retcode

    def check_output(self, stmnt):
        """Run command with arguments and return its output.
        If the return code was non-zero it raises a CalledProcessError. The
        CalledProcessError object will have the return code in the returncode
        attribute and any output in the output attribute.
        """
        retcode, stdout, _ = self(stmnt)
        if retcode != 0:
            raise CalledProcessError(retcode, repr(stmnt), stdout)
        return stdout


if not __name__ == '__main__':
    # set proxy object in front of this module
    module = sys.modules[__name__]
    gst = globals()
    sys.modules[__name__] = ModuleProxy(module, gst)
