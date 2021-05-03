import sys

lines = []
with open(sys.argv[1], 'r') as f:
    lines = f.read().split('\n')

outf = open(sys.argv[2], 'w')

# fix over-sized joint representations
for i in range(len(lines)):
    lines[i] = lines[i].replace('329.999980330467', '1.0')

# remove unneeded global scale transform
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('\tModel:') and line.find('"Null"') >= 0:
        i += 1
        while not lines[i].startswith('\t\t\tP: "DefaultAttributeIndex"'):
            i += 1
        del lines[i]
        if not lines[i].startswith('\t\t\tP: "Lcl Scaling"'):
            raise Exception('could not find Lcl Scaling for root model')
        del lines[i]
        break
    i += 1

with outf:
    outf.write('\n'.join(lines))
