from subprocess import call
import re

def getEvaluationTime(filename):
	m = re.search(r'evaluation\s+([\d\.e\-]+)', open(filename, 'r').read())
	if m:
		return float(m.group(1))
	return None

def getWeightsTime(filename):
	m = re.search(r'weights\s+([\d\.e\-]+)', open(filename, 'r').read())
	if m:
		return float(m.group(1))
	return None

def getNumberOfInvalidPoints(filename):
	m = re.search(r'invalid points\:\s+(\d+)', open(filename, 'r').read())
	if m:
		return int(m.group(1))
	return None


dst_celldims = [(10, 20),
                (20, 40),
                (40, 80),
                (80, 160),
                (160, 320),
                (320, 640),
                (640, 1280),
                (1280, 2560),]
                #(2560, 5120),
                #(5120, 10240)]


ns = []
libcf_eval = []
libcf_weights = []
esmf_eval = []
esmf_weights = []
for dstDims in dst_celldims:
	# generate the grids
	call(['python', 'generate_field.py', \
		'--dst_nj', '{}'.format(dstDims[0] + 1), \
		'--dst_ni', '{}'.format(dstDims[1] + 1), \
		])

	# comes from the coords_CF_ORCA12_GO6-2.nc file
        srcDims = (3606, 4322)

	srcN = srcDims[0] * srcDims[1]
	dstN = dstDims[0] * dstDims[1]
	ns.append(srcN * dstN)
	print('number of src * dst cells is {}'.format(srcN * dstN))

	# run esmf
	err = open('log.err', 'w')
	out = open('log.txt', 'w')
	call(['python', 'esmf_interp.py'], stdout=out, stderr=err)
	out.close()
	esmf_eval.append(getEvaluationTime('log.txt'))
	esmf_weights.append(getWeightsTime('log.txt'))

	# run libcf
	err = open('log.err', 'w')
	out = open('log.txt', 'w')
	call(['python', 'libcf_interp.py'], stdout=out, stderr=err)
	out.close()
	libcf_eval.append(getEvaluationTime('log.txt'))
	libcf_weights.append(getWeightsTime('log.txt'))
	numFails = getNumberOfInvalidPoints('log.txt')
	if numFails != 0:
		print('*** {} libcf interp failures'.format(numFails))

print(ns)
print(esmf_eval)
print(esmf_weights)
print(libcf_eval)
print(libcf_weights)
# write to file
import re, time
ta = re.sub(' ', '_', time.asctime())
f = open('run_node_interp-{}.csv'.format(ta), 'w')
f.write('src_num_cells*dst_num_cells,esmf_eval,esmf_weights,libcf_eval,libcf_weights\n')
for i in range(len(ns)):
	f.write('{},{},{},{},{}\n'.format(ns[i], esmf_eval[i], esmf_weights[i], libcf_eval[i], libcf_weights[i]))
f.close()

from matplotlib import pylab
import matplotlib
pylab.loglog(ns, esmf_eval, 'ro', markersize=8)
pylab.loglog(ns, esmf_weights, 'rs', markersize=8)
pylab.loglog(ns, libcf_eval, 'bo', markersize=8) 
pylab.loglog(ns, libcf_weights, 'bs', markersize=8)
pylab.legend(['esmf eval', 'esmf wgts', 'libcf eval', 'libcf wgts'], loc=4)
pylab.plot(ns, libcf_eval, 'b--', ns, libcf_weights, 'b--', \
	       ns, esmf_eval, 'r--', ns, esmf_weights, 'r--')
pylab.xlabel('num src cells * num dst cells')
pylab.ylabel('time [sec]')
pylab.title('bilinear interpolation')
pylab.savefig('esmf_vs_libcf.png')
pylab.show()
