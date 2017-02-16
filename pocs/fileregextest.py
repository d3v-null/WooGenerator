import tempfile
import os
import re
import csv

inFolder = "../input/"
testPath = os.path.join(inFolder, "insane.csv")

sub_params = None
sub_params = {
    'pattern'   : r',"([^"]*)\n([^"]*)",', 
    'repl'      : r',"\1\\n\2",' 
}

with open(testPath) as testFile:
    if sub_params:
        with tempfile.TemporaryFile() as tempFile:
            tempFile.write(re.sub( sub_params.get('pattern'), sub_params.get('repl'), testFile.read() ) )
            tempFile.seek(0)
            reader = csv.reader(tempFile)
            for row in reader:
                print row
    else:
        reader = csv.reader(testFile)
        for row in reader:
            print row

