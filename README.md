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

# now a more complex but mindless example
# creates a cat command object and redirect stdout to stdin of the grep command object
# stdin of the pipe statement comes from file /etc/passwd and the result of the pipe statement
# is written to /tmp/nobody.
pipe = (sh.cat('-') | sh.grep(e='nobody')) < '/etc/passwd' > '/tmp/nobody'
ret, _, stderr = sh(pipe)
```
