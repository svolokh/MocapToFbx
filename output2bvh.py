from bvh_skeleton import h36m_skeleton
import numpy as np
import sys

npy = sys.argv[1]
out = sys.argv[2]

skel = h36m_skeleton.H36mSkeleton()
output = np.load(npy)

# rotate 180 degrees around z axis
for frame in output:
    for pos in frame:
        pos[0] = -pos[0]
        pos[1] = -pos[1]

# set initial position to have hip centered on x-y plane and lowest foot on the ground
first = output[0]
h = first[skel.keypoint2index['Hip']]
l = first[skel.keypoint2index['LeftAnkle']]
r = first[skel.keypoint2index['RightAnkle']]
d = np.array([-h[0], -min(l[1], r[1]), -h[2]])
for frame in output:
    for pos in frame:
        pos += d

# rotate 90 degrees around x axis (for Maya)
for frame in output:
    for pos in frame:
        y = pos[1]
        pos[1] = pos[2]
        pos[2] = -y

skel.poses2bvh(output, output_file=out)
