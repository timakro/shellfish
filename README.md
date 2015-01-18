# shellfish
shellfish gives the subprocess module a little shell syntax

## Usage
```py
import shellfish as sh

# creates echo command object
# executes echo command and save stdout into var
echo = sh.echo('test')
_, stdout, _ = sh(echo)

# creates mount command object and pipe stdout to stdin of column command object
# executes the pipe statement and save stdout into var
pipe = sh.mount() | sh.column('-t')
_, stdout, _ = sh(pipe)

# creates grep command object with search muster nobody and uses the file /etc/passwd as stdin
# executes the grep command and save return code, stdout and stderr into vars
ret, stdout, stderr = sh(sh.grep(e='nobody') < '/etc/passwd')
